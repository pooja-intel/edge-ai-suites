#
# Apache v2 license
# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
#

""" Custom user defined function for anomaly detection in weld sensor data. """
import json
import os
import logging
import time
import warnings

log_level = os.getenv('KAPACITOR_LOGGING_LEVEL', 'INFO').upper()
enable_benchmarking = os.getenv('ENABLE_BENCHMARKING', 'false').upper() == 'TRUE'
total_no_pts = int(os.getenv('BENCHMARK_TOTAL_PTS', "0"))
logging_level = getattr(logging, log_level, logging.INFO)

# Configure logging before importing sklearnex so basicConfig takes effect
logging.basicConfig(
    level=logging_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logging.getLogger("sklearnex").setLevel(logging.INFO)

from kapacitor.udf.agent import Agent, Handler
from kapacitor.udf import udf_pb2
import numpy as np
import joblib

intel_scikitlearn_extension = os.environ.get('INTEL_SCIKITLEARN_EXTENSION', 'false').lower()
if intel_scikitlearn_extension == 'true':
    from sklearnex import patch_sklearn, config_context
    patch_sklearn()
# else:
#     # For vanilla sklearn, create a no-op context manager
#     from contextlib import nullcontext as config_context

warnings.filterwarnings(
    "ignore",
    message=".*Threading.*parallel backend is not supported by Extension for Scikit-learn.*"
)

# Primary weld current threshold
WELD_CURRENT_THRESHOLD = 50
GOOD_WELD_LABEL = "Good Weld"
NO_WELD_LABEL = "No Weld"
FEATURES = [
    "Pressure",
    "CO2 Weld Flow",
    "Feed",
    "Primary Weld Current",
    "Secondary Weld Voltage",
]
MODEL_WITH_EXPLANATION = True
logger = logging.getLogger()


def _f32(value):
    """Convert scalar numeric values to numpy float32."""
    return np.float32(value)

# Anomaly detection on the weld sensor data
class AnomalyDetectorHandler(Handler):
    """ Handler for the anomaly detection UDF. It processes incoming points
    and detects anomalies based on the weld sensor data.
    """
    def __init__(self, agent):
        self._agent = agent
        # Need to enable after model training
        self.info_data = {}
        model_name = (os.path.basename(__file__)).replace('.py', '.pkl')
        label_name = (os.path.basename(__file__)).replace('.py', '_labels.pkl')
        model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "../models/" + model_name)
        model_path = os.path.abspath(model_path)
        label_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "../models/" + label_name)
        label_path = os.path.abspath(label_path)
        self.pipeline = joblib.load(model_path)
        self.le       = joblib.load(label_path)
        self.device = os.getenv('DEVICE', 'auto').strip().lower() or 'auto'
        logger.info(f"on device: {self.device}")
        global intel_scikitlearn_extension
        logger.info(f"Intel scikit-learn extension: {intel_scikitlearn_extension}")
        global MODEL_WITH_EXPLANATION
        if MODEL_WITH_EXPLANATION:
            logger.info("Model explanations are enabled for this UDF.")
            model_json_info = (os.path.basename(__file__)).replace('.py', '.json')
            
            info_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "../models/" + model_json_info)
            info_path = os.path.abspath(info_path)

            with open(info_path, "r", encoding="utf-8") as f:
                self.info_data = json.load(f)
            logger.info(f"Model           : {self.info_data.get('algorithm', 'unknown')}")
            logger.info(f"Classes         : {len(self.info_data.get('classes', []))}")
            logger.info(f"Trained w/ Intel: {self.info_data.get('intel_patched', 'unknown')}")

        self.points_received = {}
        global total_no_pts
        self.max_points = int(total_no_pts)
        
        # batch processing state
        self._batch_points = []
        self._begin_response = None

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
        """ A batch has begun. Initialize collection for batch processing.
        """
        self._batch_points = []
        self._begin_response = udf_pb2.Response()
        self._begin_response.begin.CopyFrom(begin_req)
        logger.info("Batch started - collecting points for batch processing")
    
    def _extract_fields_from_point(self, point):
        """Extract fields from a point into a dict."""
        fields = {}
        for key, value in point.fieldsDouble.items():
            fields[key] = _f32(value)
        for key, value in point.fieldsInt.items():
            fields[key] = _f32(value)
        for key, value in point.fieldsString.items():
            fields[key] = value
        return fields
    
    def _build_explanation(self, input_row: dict, predicted_category: str, prob_map: dict, model_info: dict) -> dict:
        """Create a human-readable reason block for why a row was classified as a category."""
        stats = model_info.get("class_feature_stats", {}) if model_info else {}
        pred_stats = stats.get(predicted_category, {})
        good_stats = stats.get(GOOD_WELD_LABEL, {})

        # Sort probabilities and include top alternatives for context.
        ranked = sorted(prob_map.items(), key=lambda kv: kv[1], reverse=True)
        top_probs = [{"category": k, "probability": round(float(v), 6)} for k, v in ranked[:3]]

        signal_features = []
        for feat in FEATURES:
            if feat not in pred_stats or feat not in good_stats:
                continue
            value = _f32(input_row[feat])
            pred_mean = _f32(pred_stats[feat].get("mean", 0.0))
            pred_std = max(_f32(pred_stats[feat].get("std", 0.0)), _f32(1e-6))
            good_mean = _f32(good_stats[feat].get("mean", 0.0))
            good_std = max(_f32(good_stats[feat].get("std", 0.0)), _f32(1e-6))

            # Positive score means closer to predicted class profile than Good Weld profile.
            z_to_pred = _f32(abs(value - pred_mean) / pred_std)
            z_to_good = _f32(abs(value - good_mean) / good_std)
            evidence = _f32(z_to_good - z_to_pred)

            signal_features.append(
                {
                    "feature": feat,
                    "value": round(float(value), 6),
                    "predicted_mean": round(float(pred_mean), 6),
                    "good_weld_mean": round(float(good_mean), 6),
                    "evidence_score": round(float(evidence), 6),
                }
            )

        signal_features.sort(key=lambda x: x["evidence_score"], reverse=True)
        top_signals = signal_features[:3]

        if top_signals:
            reason = (
                f"Classified as {predicted_category} because key signals "
                f"({', '.join(s['feature'] for s in top_signals)}) align more with "
                f"{predicted_category} profile than Good Weld profile."
            )
        else:
            reason = (
                f"Classified as {predicted_category} based on model probability ranking; "
                "class profile statistics were not available."
            )

        return {
            "reason": reason,
            "top_probabilities": top_probs,
            "top_signal_features": top_signals,
        }


    def point(self, point):
        """ A point has arrived. Accumulate it for batch processing.
        """
        # Ensure downstream Kapacitor expressions can always resolve this field.
        if "anomaly_status" not in point.fieldsDouble:
            point.fieldsDouble["anomaly_status"] = 0.0
        self._batch_points.append(point)


    def end_batch(self, end_req):
        """ The batch is complete. Process all accumulated points using vectorized predictions.
        """
        batch_start_time = time.time_ns()
        batch_size = len(self._batch_points)
        logger.info("Processing batch of %d points", batch_size)

        # Write begin batch response
        self._agent.write_response(self._begin_response)

        if batch_size == 0:
            # Empty batch - just send end
            response = udf_pb2.Response()
            response.end.CopyFrom(end_req)
            self._agent.write_response(response)
            return

        try:
            # Extract valid points for inference and prepare batch data
            valid_points_info = []  # list of (index, point, fields_dict, is_valid_for_inference)
            x_values_for_batch = []
            
            for i, point in enumerate(self._batch_points):
                # Ensure anomaly_status always exists on every point.
                if "anomaly_status" not in point.fieldsDouble:
                    point.fieldsDouble["anomaly_status"] = 0.0
                
                fields = self._extract_fields_from_point(point)
                stream_src = point.tags.get("source") or fields.get("source")
                
                global enable_benchmarking
                if enable_benchmarking:
                    if stream_src not in self.points_received:
                        self.points_received[stream_src] = 0
                    if self.points_received[stream_src] >= self.max_points:
                        valid_points_info.append((i, point, fields, False))
                        continue
                    self.points_received[stream_src] += 1
                
                weld_current = fields.get("Primary Weld Current", _f32(0.0))
                
                # Check if point qualifies for inference
                if weld_current >= WELD_CURRENT_THRESHOLD:
                    missing_features = [f for f in FEATURES if f not in fields]
                    if not missing_features:
                        x_values_for_batch.append([
                            _f32(fields["Pressure"]),
                            _f32(fields["CO2 Weld Flow"]),
                            _f32(fields["Feed"]),
                            _f32(fields["Primary Weld Current"]),
                            _f32(fields["Secondary Weld Voltage"]),
                        ])
                        valid_points_info.append((i, point, fields, True))
                    else:
                        logger.warning("Point %d: Missing features %s", i, missing_features)
                        valid_points_info.append((i, point, fields, False))
                else:
                    valid_points_info.append((i, point, fields, False))
            
            # Vectorized batch prediction
            predictions = None
            predictions_proba = None
            if x_values_for_batch:
                x_array = np.array(x_values_for_batch, dtype=np.float32)
                if intel_scikitlearn_extension == 'true':
                    with config_context(target_offload=self.device, allow_fallback_to_host=True):
                        predictions = self.pipeline.predict(x_array)
                        predictions_proba = self.pipeline.predict_proba(x_array)
                else:
                    predictions = self.pipeline.predict(x_array)
                    predictions_proba = self.pipeline.predict_proba(x_array)
            
            # Map predictions back to points and process
            pred_idx = 0
            for i, point, fields, is_valid in valid_points_info:
                point_start_time = time.time_ns()
                
                if is_valid:
                    # This point was part of the vectorized batch
                    pred_label_idx = predictions[pred_idx]
                    pred_proba = predictions_proba[pred_idx]
                    pred_idx += 1
                    
                    classes = list(self.le.classes_)
                    prob_map = {cls: float(_f32(p)) for cls, p in zip(classes, pred_proba)}
                    predicted_category = self.le.inverse_transform([pred_label_idx])[0]
                    
                    point.fieldsString["predicted_category"] = str(predicted_category)
                    good_weld_prob = _f32(prob_map.get(GOOD_WELD_LABEL, 0.0))
                    good_defect = _f32(good_weld_prob * _f32(100.0))
                    bad_defect = _f32((_f32(1.0) - good_weld_prob) * _f32(100.0))
                    confidence = round(float(_f32(np.max(pred_proba))), 6)
                    
                    if MODEL_WITH_EXPLANATION:
                        explanation = self._build_explanation(fields, predicted_category, prob_map, self.info_data)
                    else:
                        explanation = "N/A"
                    
                    data_prediction = {
                        "predicted_category": predicted_category,
                        "is_defect": predicted_category != GOOD_WELD_LABEL,
                        "defect_probability": round(float(_f32(_f32(1.0) - good_weld_prob)), 6),
                        "good_weld_probability": round(float(good_weld_prob), 6),
                        "confidence": confidence,
                        "probabilities": prob_map,
                        "explanation": explanation,
                    }
                    
                    point.fieldsString["prediction_details"] = json.dumps(data_prediction)
                    point.fieldsDouble["Good Weld"] = round(float(good_defect), 2)
                    point.fieldsDouble["Defective Weld"] = round(float(bad_defect), 2)
                    
                    if bad_defect > _f32(50):
                        point.fieldsDouble["anomaly_status"] = 1.0
                    else:
                        point.fieldsDouble["anomaly_status"] = 0.0
                    
                    logger.debug("Point %d: Good Weld: %.2f%%, Defective Weld: %.2f%%", i, good_defect, bad_defect)
                else:
                    # Point below threshold or missing features
                    weld_current = fields.get("Primary Weld Current", _f32(0.0))
                    if weld_current < WELD_CURRENT_THRESHOLD:
                        point.fieldsString["predicted_category"] = NO_WELD_LABEL
                        logger.debug(
                            "Point %d: Primary Weld Current %.2f < threshold %d. Classified as %s.",
                            i, weld_current, WELD_CURRENT_THRESHOLD, NO_WELD_LABEL,
                        )
                    point.fieldsDouble["Good Weld"] = 0.0
                    point.fieldsDouble["Defective Weld"] = 0.0
                    point.fieldsDouble["anomaly_status"] = 0.0
                
                time_now = time.time_ns()
                processing_time = time_now - point_start_time
                end_end_time = time_now - point.time
                point.fieldsDouble["processing_time"] = processing_time
                point.fieldsDouble["end_end_time"] = end_end_time
                
                # Write point response
                response = udf_pb2.Response()
                if "anomaly_status" not in point.fieldsDouble:
                    point.fieldsDouble["anomaly_status"] = 0.0
                response.point.CopyFrom(point)
                self._agent.write_response(response)
        
        except Exception:
            logger.exception("Error while processing batch; emitting safe defaults")
            for point in self._batch_points:
                if "anomaly_status" not in point.fieldsDouble:
                    point.fieldsDouble["anomaly_status"] = 0.0
                point.fieldsDouble["Good Weld"] = 0.0
                point.fieldsDouble["Defective Weld"] = 0.0
                response = udf_pb2.Response()
                response.point.CopyFrom(point)
                self._agent.write_response(response)
        
        # Write end batch response
        response = udf_pb2.Response()
        response.end.CopyFrom(end_req)
        self._agent.write_response(response)
        
        batch_end_time = time.time_ns()
        batch_processing_time = (batch_end_time - batch_start_time) / 1e6
        logger.info("Batch of %d points processed in %.2f ms (%.2f ms/point)",
                     batch_size, batch_processing_time,
                     batch_processing_time / batch_size if batch_size > 0 else 0)


if __name__ == '__main__':
    # Create an agent
    agent = Agent()

    # Create a handler and pass it an agent so it can write points
    h = AnomalyDetectorHandler(agent)

    # Set the handler on the agent
    agent.handler = h

    # Anything printed to STDERR from a UDF process gets captured
    # into the Kapacitor logs.
    agent.start()
    agent.wait()
