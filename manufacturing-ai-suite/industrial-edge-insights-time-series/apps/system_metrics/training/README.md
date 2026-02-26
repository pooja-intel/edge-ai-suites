# Predictive Maintenance ML Training

This script trains machine learning models for predictive maintenance using a labeled synthetic dataset of system metrics. The trained models can detect anomalies and predict failures in edge computing environments.

## Overview

`train_ml_models.py` trains three complementary models:

| Model | Algorithm | Purpose | Output File |
|---|---|---|---|
| Anomaly Detector | Random Forest | Binary classification — normal vs. anomalous | `anomaly_detector_model.pkl` |
| Failure Predictor | Gradient Boosting | Predicts whether a failure will occur within 60 minutes | `failure_predictor_model.pkl` |
| Anomaly Type Classifier | Random Forest | Multi-class classification of anomaly type | `anomaly_type_classifier_model.pkl` |
| Feature Scaler | StandardScaler | Normalizes input features for inference | `feature_scaler.pkl` |

## Dataset

The models are trained on a **synthetic dataset** (`tick_synthetic_pm_dataset.csv`) that simulates realistic system behavior including normal operation and various failure modes. The dataset contains the following labeled columns:

- `anomaly` — binary flag (0 = normal, 1 = anomalous)
- `failure_within_horizon` — binary flag indicating a failure will occur within 60 minutes
- `anomaly_type` — integer label for anomaly category:

| Value | Type |
|---|---|
| 0 | Normal |
| 1 | CPU Spike |
| 2 | Memory Leak |
| 3 | I/O Bottleneck |
| 4 | Network Issue |
| 5 | Container Fault |

## Input Features

All models use the same set of 20 system metric features:

| Category | Features |
|---|---|
| CPU | `cpu_total_pct`, `cpu_user_pct`, `cpu_system_pct`, `cpu_iowait_pct` |
| Memory | `mem_used_pct`, `swap_used_pct` |
| Disk | `disk_used_pct`, `disk_read_bps`, `disk_write_bps`, `disk_latency_ms`, `disk_iops` |
| Network | `net_in_bps`, `net_out_bps`, `net_err_rate` |
| System Load | `load1`, `proc_running` |
| Container | `ctr_cpu_total_pct`, `ctr_mem_used_pct_of_limit`, `ctr_unhealthy_count`, `ctr_exited_count` |

## Usage

### Prerequisites

```bash
pip install pandas numpy scikit-learn matplotlib seaborn joblib
```

### Run Training

Place `tick_synthetic_pm_dataset.csv` in the same directory, then run:

```bash
python train_ml_models.py
```

The script prints training progress, evaluation metrics (accuracy, ROC AUC, classification report, confusion matrix), and top feature importances for each model.

### Real-Time Inference

After training, the `predict_realtime()` method accepts a dictionary of current metric values and returns:

```python
{
    "is_anomaly": True,
    "anomaly_probability": 0.91,
    "failure_within_60min": False,
    "failure_probability": 0.42,
    "alert_level": "WARNING"   # NORMAL | WARNING | CRITICAL
}
```

Alert levels are determined by failure probability:

| Level | Condition |
|---|---|
| `CRITICAL` | failure probability > 0.8 |
| `WARNING` | failure probability > 0.6 |
| `NORMAL` | failure probability <= 0.6 |

## Output Files

After a successful run, the following files are saved to the working directory:

```
anomaly_detector_model.pkl        # Random Forest anomaly detector
failure_predictor_model.pkl       # Gradient Boosting failure predictor
anomaly_type_classifier_model.pkl # Random Forest anomaly type classifier
feature_scaler.pkl                # Fitted StandardScaler for inference
```
