#!/usr/bin/env python3
#
# Apache v2 license
# Copyright (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
#

""" Custom user defined function for predictive maintenance anomaly detection
on system metrics (CPU, memory, disk, network, etc.). """

import os
import logging
import pickle
import joblib
import time
import math
import warnings
import numpy as np
from kapacitor.udf.agent import Agent, Handler
from kapacitor.udf import udf_pb2

warnings.filterwarnings('ignore')

log_level = os.getenv('KAPACITOR_LOGGING_LEVEL', 'INFO').upper()
logging_level = getattr(logging, log_level, logging.INFO)

# Configure logging
logging.basicConfig(
    level=logging_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)

logger = logging.getLogger()

# Feature columns (must match training)
FEATURE_COLUMNS = [
    'cpu_total_pct', 'cpu_user_pct', 'cpu_system_pct', 'cpu_iowait_pct',
    'mem_used_pct', 'swap_used_pct',
    'disk_used_pct', 'disk_read_bps', 'disk_write_bps', 'disk_latency_ms', 'disk_iops',
    'net_in_bps', 'net_out_bps', 'net_err_rate',
    'load1', 'proc_running',
    'ctr_cpu_total_pct', 'ctr_mem_used_pct_of_limit', 'ctr_unhealthy_count', 'ctr_exited_count'
]


class SystemAnomalyDetectorHandler(Handler):
    """ Handler for system anomaly detection UDF. It processes incoming metrics
    and detects anomalies using ML models.
    """
    
    def __init__(self, agent):
        self._agent = agent
        
        # Load trained ML models
        # model_dir = os.getenv('MODEL_PATH', '/models')
        model_dir = "/tmp/system_metrics/models/"
        try:
            anomaly_model_path = os.path.join(model_dir, 'anomaly_detector_model.pkl')
            failure_model_path = os.path.join(model_dir, 'failure_predictor_model.pkl')
            type_model_path = os.path.join(model_dir, 'anomaly_type_classifier_model.pkl')
            scaler_path = os.path.join(model_dir, 'feature_scaler.pkl')
            
            self.anomaly_model = joblib.load(anomaly_model_path)
            self.failure_model = joblib.load(failure_model_path)
            self.type_model = joblib.load(type_model_path)
            self.scaler = joblib.load(scaler_path)
                
            logger.info("ML models loaded successfully from %s", model_dir)
            self.models_loaded = True
            
        except Exception as e:
            logger.error("Failed to load ML models: %s", str(e))
            logger.warning("UDF will run without predictions")
            self.models_loaded = False
            self.anomaly_model = None
            self.failure_model = None
            self.type_model = None
            self.scaler = None
        
        self.points_received = 0
        self.anomalies_detected = 0

    def info(self):
        """ Return the InfoResponse describing the properties of this Handler """
        response = udf_pb2.Response()
        response.info.wants = udf_pb2.STREAM
        response.info.provides = udf_pb2.STREAM
        return response

    def init(self, init_req):
        """ Initialize the Handler with the provided options """
        response = udf_pb2.Response()
        response.init.success = True
        return response

    def snapshot(self):
        """ Create a snapshot of the running state of the process """
        response = udf_pb2.Response()
        response.snapshot.snapshot = b''
        return response

    def restore(self, restore_req):
        """ Restore a previous snapshot """
        response = udf_pb2.Response()
        response.restore.success = False
        response.restore.error = 'not implemented'
        return response

    def begin_batch(self, begin_req):
        """ A batch has begun """
        raise Exception("not supported - use stream processing")

    def extract_features(self, point):
        """
        Extract features from Kapacitor point
        
        Args:
            point: Kapacitor point with fieldsDouble containing metrics
            
        Returns:
            dict with feature values
        """
        features = {}
        
        # Extract all available metrics from point.fieldsDouble
        for field_name in FEATURE_COLUMNS:
            if field_name in point.fieldsDouble:
                features[field_name] = point.fieldsDouble[field_name]
            else:
                # Default to 0 if field not present
                features[field_name] = 0.0
        
        # Calculate disk_iops if not present
        if 'disk_iops' not in point.fieldsDouble:
            disk_read = features.get('disk_read_bps', 0)
            disk_write = features.get('disk_write_bps', 0)
            features['disk_iops'] = (disk_read + disk_write) / 4096
        
        # Calculate net_err_rate if not present
        if 'net_err_rate' not in point.fieldsDouble:
            net_in = features.get('net_in_bps', 1)
            net_out = features.get('net_out_bps', 1)
            err_in = features.get('net_err_in', 0)
            err_out = features.get('net_err_out', 0)
            total_bytes = max(net_in + net_out, 1)
            features['net_err_rate'] = (err_in + err_out) / total_bytes
        
        return features

    def print_metrics(self, point, features, host):
        """Print received metric values for debugging"""
        logger.info("="*70)
        logger.info("RECEIVED METRICS - Host: %s", host)
        logger.info("-"*70)
        logger.info("  CPU Metrics: Total: %6.1f%%, User: %6.1f%%, System: %6.1f%%, I/O Wait: %6.1f%%", features.get('cpu_total_pct', 0), features.get('cpu_user_pct', 0), features.get('cpu_system_pct', 0), features.get('cpu_iowait_pct', 0))
        logger.info("  Memory Metrics: Used: %6.1f%%, Swap Used: %6.1f%%", features.get('mem_used_pct', 0), features.get('swap_used_pct', 0))
        logger.info("  Disk Metrics: Used: %6.1f%%, Read: %6.0f bytes/s, Write: %6.0f bytes/s, Latency: %6.1f ms, IOPS: %6.1f", features.get('disk_used_pct', 0), features.get('disk_read_bps', 0), features.get('disk_write_bps', 0), features.get('disk_latency_ms', 0), features.get('disk_iops', 0))
        logger.info("  Network Metrics: In: %6.0f bytes/s, Out: %6.0f bytes/s, Error Rate: %6.4f", features.get('net_in_bps', 0), features.get('net_out_bps', 0), features.get('net_err_rate', 0))
        logger.info("  System Metrics: Load (1min): %6.2f, Proc Running: %6.0f", features.get('load1', 0), features.get('proc_running', 0))
        logger.info("  Container Metrics: CPU: %6.1f%%, Memory: %6.1f%%, Unhealthy: %6.0f, Exited: %6.0f; %s", features.get('ctr_cpu_total_pct', 0), features.get('ctr_mem_used_pct_of_limit', 0), features.get('ctr_unhealthy_count', 0), features.get('ctr_exited_count', 0), "="*70)

    def predict(self, features):
        """
        Make anomaly and failure predictions using ML models
        
        Args:
            features: dict with feature values
            
        Returns:
            dict with predictions
        """
        if not self.models_loaded:
            return {
                'is_anomaly': False,
                'anomaly_probability': 0.0,
                'failure_within_60min': False,
                'failure_probability': 0.0,
                'anomaly_type': 0,
                'anomaly_type_name': 'UNKNOWN',
                'alert_level': 'UNKNOWN'
            }
        
        try:
            # Convert features to array in correct order
            feature_array = np.array([[features[col] for col in FEATURE_COLUMNS]])
            
            # Scale features
            features_scaled = self.scaler.transform(feature_array)
            
            # Anomaly type label map (must match training)
            ANOMALY_TYPE_NAMES = {
                0: 'Normal',
                1: 'CPU Spike',
                2: 'Memory Leak',
                3: 'I/O Bottleneck',
                4: 'Network',
                5: 'Container'
            }

            # Make predictions
            is_anomaly = bool(self.anomaly_model.predict(features_scaled)[0])
            anomaly_prob = float(self.anomaly_model.predict_proba(features_scaled)[0][1])
            
            failure_soon = bool(self.failure_model.predict(features_scaled)[0])
            failure_prob = float(self.failure_model.predict_proba(features_scaled)[0][1])

            # Classify anomaly type (only meaningful when an anomaly is detected)
            if is_anomaly:
                anomaly_type = int(self.type_model.predict(features_scaled)[0])
            else:
                anomaly_type = 0
            anomaly_type_name = ANOMALY_TYPE_NAMES.get(anomaly_type, f'Type{anomaly_type}')
            
            # Determine alert level
            if failure_prob > 0.8:
                alert_level = 'CRITICAL'
            elif failure_prob > 0.6:
                alert_level = 'WARNING'
            elif is_anomaly:
                alert_level = 'INFO'
            else:
                alert_level = 'NORMAL'
            
            return {
                'is_anomaly': is_anomaly,
                'anomaly_probability': anomaly_prob,
                'failure_within_60min': failure_soon,
                'failure_probability': failure_prob,
                'anomaly_type': anomaly_type,
                'anomaly_type_name': anomaly_type_name,
                'alert_level': alert_level
            }
            
        except Exception as e:
            logger.error("Prediction error: %s", str(e))
            return {
                'is_anomaly': False,
                'anomaly_probability': 0.0,
                'failure_within_60min': False,
                'failure_probability': 0.0,
                'anomaly_type': 0,
                'anomaly_type_name': 'ERROR',
                'alert_level': 'ERROR'
            }

    def point(self, point):
        """ Process incoming point """
        start_time = time.time_ns()
        
        # Get host tag
        host = point.tags.get("host", "unknown")
        
        # Extract features
        features = self.extract_features(point)
        
        # Print received metrics (only if log level is INFO or DEBUG)
        if logger.level <= logging.INFO:
            self.print_metrics(point, features, host)
        
        # Make prediction
        prediction = self.predict(features)
        
        # Log prediction results
        logger.info("PREDICTIONS:")
        logger.info("  Anomaly:           %s (%.1f%%)",
                   "YES" if prediction['is_anomaly'] else "NO",
                   prediction['anomaly_probability'] * 100)
        logger.info("  Failure Risk:      %s (%.1f%%)",
                   "YES" if prediction['failure_within_60min'] else "NO",
                   prediction['failure_probability'] * 100)
        logger.info("  Anomaly Type:      %s (%d)",
                   prediction['anomaly_type_name'], prediction['anomaly_type'])
        
        # Icon for alert level
        logger.info("  Alert Level:         %s", prediction['alert_level'])
        
        # Track statistics
        self.points_received += 1
        if prediction['is_anomaly']:
            self.anomalies_detected += 1
            logger.warning("ANOMALY DETECTED! (Total: %d/%d = %.1f%%)",
                         self.anomalies_detected, self.points_received,
                         (self.anomalies_detected / self.points_received) * 100)
        
        # Add predictions to point
        point.fieldsDouble["is_anomaly"] = 1.0 if prediction['is_anomaly'] else 0.0
        point.fieldsDouble["anomaly_probability"] = prediction['anomaly_probability']
        point.fieldsDouble["failure_within_60min"] = 1.0 if prediction['failure_within_60min'] else 0.0
        point.fieldsDouble["failure_probability"] = prediction['failure_probability']
        point.fieldsInt["anomaly_type"] = prediction['anomaly_type']
        point.fieldsString["anomaly_type_name"] = prediction['anomaly_type_name']
        point.fieldsString["alert_level"] = prediction['alert_level']
        
        # Add processing time
        end_time = time.time_ns()
        processing_time = (end_time - start_time) / 1_000_000  # Convert to milliseconds
        point.fieldsDouble["processing_time_ms"] = processing_time
        
        logger.debug("Processing took %.2f ms", processing_time)
        logger.info("-"*70 + "\n")
        
        # Send response
        response = udf_pb2.Response()
        response.point.CopyFrom(point)
        self._agent.write_response(response, True)

    def end_batch(self, end_req):
        """ The batch is complete """
        raise Exception("not supported - use stream processing")


if __name__ == '__main__':
    # Create an agent
    agent = Agent()

    # Create a handler and pass it an agent so it can write points
    h = SystemAnomalyDetectorHandler(agent)

    # Set the handler on the agent
    agent.handler = h

    logger.info("="*70)
    logger.info("SYSTEM ANOMALY DETECTOR UDF STARTED")
    logger.info("="*70)
    logger.info("Model Directory: %s", os.getenv('MODEL_PATH', '/models'))
    logger.info("Log Level: %s", log_level)
    logger.info("="*70)

    # Anything printed to STDERR from a UDF process gets captured
    # into the Kapacitor logs.
    agent.start()
    agent.wait()
    
    logger.info("UDF stopped. Total points: %d, Anomalies: %d",
               h.points_received, h.anomalies_detected)
