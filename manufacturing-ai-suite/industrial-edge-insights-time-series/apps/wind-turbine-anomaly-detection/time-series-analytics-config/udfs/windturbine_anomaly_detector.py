#
# Apache v2 license
# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
#

""" Custom user defined function for anomaly detection on 
the windturbine speed and generated power data. """

import os
import logging
import time
import warnings
from kapacitor.udf.agent import Agent, Handler
from kapacitor.udf import udf_pb2
import numpy as np
intel_scikitlearn_extension = os.environ.get('INTEL_SCIKITLEARN_EXTENSION', 'true').lower()
if intel_scikitlearn_extension == 'true':
    from sklearnex import patch_sklearn, config_context
    patch_sklearn()
    from sklearnex.linear_model import LinearRegression
else:
    from sklearn.linear_model import LinearRegression

warnings.filterwarnings(
    "ignore",
    message=".*Threading.*parallel backend is not supported by Extension for Scikit-learn.*"
)


log_level = os.getenv('KAPACITOR_LOGGING_LEVEL', 'INFO').upper()
enable_benchmarking = os.getenv('ENABLE_BENCHMARKING', 'false').upper() == 'TRUE'
total_no_pts = int(os.getenv('BENCHMARK_TOTAL_PTS', "0"))
logging_level = getattr(logging, log_level, logging.INFO)

# Configure logging
logging.basicConfig(
    level=logging_level,  # Set the log level to DEBUG
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Log format
)

logger = logging.getLogger()

# Anomaly detection on the windturbine speed and generated power data
class AnomalyDetectorHandler(Handler):
    """ Handler for the anomaly detection UDF. It processes incoming points
    and detects anomalies based on the wind speed and generated power data.
    """
    def __init__(self, agent):
        self._agent = agent
        # This UDF is DBSCAN-based and does not require loading a persisted model file.

        self.device = os.getenv('DEVICE', 'auto').lower()

        # wind speed and active power field name in the influxdb measurements
        self.x_name = "wind_speed"
        self.y_name = "grid_active_power"

        # Residual threshold percentile for anomaly labeling in each batch
        self.anomaly_percentile = float(os.getenv('ANOMALY_PERCENTILE', '95'))

        self.points_received = {}
        global total_no_pts
        self.max_points = int(total_no_pts)
        self._batch_point_counter = 0
        self._batch_points = []   # list of raw kapacitor Point objects for the current batch
        self._batch_begin_ns = None

    def info(self):
        """ Return the InfoResponse. Describing the properties of this Handler
        """
        response = udf_pb2.Response()
        response.info.wants = udf_pb2.BATCH
        response.info.provides = udf_pb2.BATCH
        return response

    def init(self, init_req):
        """ Initialize the Handler with the provided options.
        """
        response = udf_pb2.Response()
        response.init.success = True
        return response

    def snapshot(self):
        """ Create a snapshot of the running state of the process.
        """
        response = udf_pb2.Response()
        response.snapshot.snapshot = b''
        return response

    def restore(self, restore_req):
        """ Restore a previous snapshot.
        """
        response = udf_pb2.Response()
        response.restore.success = False
        response.restore.error = 'not implemented'
        return response

    def begin_batch(self, begin_req):
        """ A batch has begun — reset accumulators for the new window.
        """
        self._batch_begin_ns = time.time_ns()
        logger.info(
            "Batch started: group=%s, size=%d, begin_time_ns=%d",
            begin_req.group,
            begin_req.size,
            self._batch_begin_ns,
        )
        self._batch_points = []
        self._batch_point_counter = 0
        response = udf_pb2.Response()
        response.begin.CopyFrom(begin_req)
        self._agent.write_response(response)

    def point(self, point):
        """ A point has arrived — accumulate for batch processing in end_batch.
        """
        self._batch_point_counter += 1
        logger.debug("Accumulated point %d for source %s",
                     self._batch_point_counter,
                     point.tags.get("source", "<unknown>"))
        self._batch_points.append(point)

    def process_batch(self, points):
        """Fit LinearRegression on a batch and return residual stats for anomaly labeling."""
        # Build regression dataset y=grid_active_power, X=[wind_speed].
        process_batch_start_ns = time.time_ns()
        valid_idx = []
        x_values = []
        y_values = []
        for i, p in enumerate(points):
            x = p.fieldsDouble.get(self.x_name)
            y = p.fieldsDouble.get(self.y_name)
            if x is not None and y is not None:
                valid_idx.append(i)
                x_values.append([x])
                y_values.append(y)

        residuals = None
        threshold = None
        if x_values:
            X = np.array(x_values, dtype=np.float32)
            y = np.array(y_values, dtype=np.float32)
            model = LinearRegression()
            if intel_scikitlearn_extension == 'true':
                logger.info("Fitting LinearRegression with Intel Extension for Scikit-learn on device: %s", self.device)
                if self.device == 'cpu':
                    # patch_sklearn() already accelerates CPU — skip config_context
                    # to avoid per-batch context manager overhead on CPU path.
                    model.fit(X, y)
                    pred = model.predict(X)
                else:
                    # GPU / XPU path: config_context is required for device offload.
                    with config_context(target_offload=self.device, allow_fallback_to_host=True):
                        model.fit(X, y)
                        pred = model.predict(X)
            else:
                logger.info("Fitting LinearRegression with scikit-learn on CPU")
                model.fit(X, y)
                pred = model.predict(X)

            residuals = np.abs(y - pred)
            threshold = np.percentile(residuals, self.anomaly_percentile)
            logger.info(
                "LinearRegression residual threshold at %.1f percentile: %.6f",
                self.anomaly_percentile,
                float(threshold),
            )
        process_batch_end_ns = time.time_ns()
        logger.info("Time taken to process batch of %d points: %.6f ms",
                    len(points),
                    (process_batch_end_ns - process_batch_start_ns) / 1e6)

        return valid_idx, residuals, threshold

    def end_batch(self, end_req):
        """ The batch is complete — fit LinearRegression and write residual-based anomalies.
        """
        start_time = time.time_ns()

        points = self._batch_points
        valid_idx, residuals, threshold = self.process_batch(points)

        # Write every point back with anomaly_status annotated
        for i, point in enumerate(points):
            if residuals is not None and i in valid_idx:
                pos = valid_idx.index(i)
                current_residual = float(residuals[pos])
                point.fieldsDouble["residual_error"] = current_residual
                point.fieldsDouble["anomaly_status"] = 1.0 if current_residual > float(threshold) else 0.0
            else:
                point.fieldsDouble["anomaly_status"] = 0.0

            point.fieldsDouble["processing_time"] = float(time.time_ns() - start_time)
            response = udf_pb2.Response()
            response.point.CopyFrom(point)
            self._agent.write_response(response, True)

        logger.info("Batch write-back complete in %.2f ms",
                    (time.time_ns() - start_time) / 1e6)

        # Write batch footer
        response = udf_pb2.Response()
        response.end.CopyFrom(end_req)
        self._agent.write_response(response)
        batch_end_ns = time.time_ns()
        if self._batch_begin_ns is not None:
            batch_duration_ms = (batch_end_ns - self._batch_begin_ns) / 1e6
            logger.info(
                "Batch ended: processing %d points, group=%s, end_time_ns=%d, batch_duration_ms=%.3f",
                self._batch_point_counter,
                end_req.group,
                batch_end_ns,
                batch_duration_ms,
            )
        else:
            logger.info(
                "Batch ended: processing %d points, group=%s, end_time_ns=%d, batch_duration_ms=unavailable",
                self._batch_point_counter,
                end_req.group,
                batch_end_ns,
            )


if __name__ == '__main__':
    # Create an agent
    agent = Agent()

    # Create a handler and pass it an agent so it can write points
    try:
        h = AnomalyDetectorHandler(agent)
    except Exception as error:
        logger.exception("Failed to initialize windturbine_anomaly_detector UDF: %s", error)
        raise

    # Set the handler on the agent
    agent.handler = h

    # Anything printed to STDERR from a UDF process gets captured
    # into the Kapacitor logs.
    agent.start()
    agent.wait()
