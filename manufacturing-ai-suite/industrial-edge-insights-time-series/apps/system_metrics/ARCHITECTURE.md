# System Metrics Predictive Maintenance — Architecture Guide

This document describes the end-to-end data flow of the system metrics predictive maintenance sample application, from raw OS-level metric collection through stream processing, ML inference, and alerting.

---

## Overview

```
┌─────────────┐    ┌──────────────┐    ┌──────────────────────────────────────────┐    ┌──────────────┐
│   Host OS   │───▶│   Telegraf   │───▶│              Kapacitor                   │───▶│   InfluxDB   │
│  + Docker   │    │  (collector) │    │  TICKscript ──▶ UDF (ML inference)       │    │ (dataout)    │
└─────────────┘    └──────────────┘    └──────────────────────────────────────────┘    └──────────────┘
                                                                                               │
                                                                                        ┌──────▼───────┐
                                                                                        │    Grafana   │
                                                                                        │  (dashboard) │
                                                                                        └──────────────┘
```

---

## 1. Data Collection — Telegraf

Telegraf runs as an agent on the monitored host and collects OS and container metrics using the following input plugins:

| Plugin | Measurement Name | Key Fields Collected |
|---|---|---|
| `inputs.cpu` | `cpu` | `usage_user`, `usage_system`, `usage_idle`, `usage_iowait` |
| `inputs.mem` | `mem` | `used_percent` |
| `inputs.swap` | `swap` | `used_percent` |
| `inputs.disk` | `disk` | `used_percent` (root `/` path) |
| `inputs.diskio` | `diskio` | `read_bytes`, `write_bytes`, `io_await` (device `sda`) |
| `inputs.net` | `net` | `bytes_recv`, `bytes_sent`, `err_in`, `err_out` (interface `eth0`) |
| `inputs.system` | `system` | `load1` |
| `inputs.processes` | `processes` | `running` |
| `inputs.docker` | `docker_container_cpu`, `docker_container_mem` | `usage_percent` |

**Configuration highlights:**
- Collection interval: `1s`
- Flush interval: `0.1s`
- All metrics are tagged with `host`
- Output: InfluxDB database `datain`, retention policy `autogen`

---

## 2. Stream Processing — Kapacitor TICKscript

**File:** `time-series-analytics-config/tick_scripts/system_metrics_anomaly_detector.tick`

The TICKscript reads the raw metric streams from InfluxDB and prepares a unified feature vector for the ML model. It runs entirely in **stream mode** (row-by-row, not batch).

### 2.1 Per-Metric Windowing

Each measurement is read as a separate stream and aggregated using a **10-second tumbling window** (`period(10s).every(10s)`). The mean value over the window is used, smoothing out sub-second noise.

```
stream → from(measurement) → window(10s) → mean(field) → named variable
```

### 2.2 Derivative for Cumulative Counters

Several Telegraf plugins report monotonically increasing counters (total bytes since boot). The TICKscript uses `|derivative()` to convert these to **per-second rates** before windowing:

| Raw Counter Field | Derived Field | Notes |
|---|---|---|
| `diskio.read_bytes` | `disk_read_bps` | bytes/sec, non-negative |
| `diskio.write_bytes` | `disk_write_bps` | bytes/sec, non-negative |
| `net.bytes_recv` | `net_in_bps` | bytes/sec, non-negative |
| `net.bytes_sent` | `net_out_bps` | bytes/sec, non-negative |
| `net.err_in` | `net_err_in` | errors/sec, non-negative |
| `net.err_out` | `net_err_out` | errors/sec, non-negative |

> **Note:** The `"elapsed time was 0"` error from Kapacitor occurs when two consecutive points for a counter field have identical timestamps, making the derivative calculation undefined. This is normal on startup or during reconnects and is safely ignored — Kapacitor skips the point and continues.

Docker container streams use a **60-second window** (wider, as container metrics arrive less frequently) with a 10-second emit cadence.

### 2.3 Multi-Stream Join

All 10 metric streams are joined into a single unified point:

```
cpu + mem + swap + disk + diskio + net + system + processes + docker_cpu + docker_mem
  └──────────────────────── join(tolerance=30s, fill=0.0) ────────────────────────────▶ data0
```

- **Tolerance of 30s** allows for timing skew between different measurement sources.
- Missing fields (e.g., if Docker is not running) are filled with `0.0` via `|default()`.
- Joined fields are then flattened with `|eval()` into top-level field names matching the ML model's expected input schema.

### 2.4 UDF Invocation

The unified point is passed to the Kapacitor UDF:

```
data0 → @system_metrics_anomaly_detector()
```

Kapacitor communicates with the UDF process over a Unix socket using Protocol Buffers. The UDF receives each point, annotates it with predictions, and returns it.

### 2.5 Output

The enriched point (original metrics + ML predictions) is written to two sinks:

**InfluxDB** — measurement `system-anomaly-predictions` in the `datain` database, enabling historical trending and Grafana dashboards.

**Kapacitor Alert** — raises alerts based on the `alert_level` field returned by the UDF:

| `alert_level` value | Kapacitor Level | Trigger condition |
|---|---|---|
| `INFO` | Info | Anomaly detected, low failure risk |
| `WARNING` | Warn | Failure probability > 60% |
| `CRITICAL` | Critical | Failure probability > 80% |

Alerts fire only on **state changes** (`.stateChangesOnly()`) to avoid repeated notifications for sustained conditions. Alert details are logged to `/var/log/kapacitor/system_anomaly_alerts.log`.

---

## 3. ML Inference — Kapacitor UDF

**File:** `time-series-analytics-config/udfs/system_metrics_anomaly_detector.py`

The UDF runs as a long-lived Python process registered with Kapacitor. It operates in **STREAM** mode — processing one point at a time with low latency.

### 3.1 Model Loading

On startup, the UDF loads four artifacts from `/tmp/system_metrics/models/` (configurable via `MODEL_PATH`):

| File | Contents |
|---|---|
| `anomaly_detector_model.pkl` | Random Forest — binary anomaly classifier |
| `failure_predictor_model.pkl` | Gradient Boosting — 60-minute failure predictor |
| `anomaly_type_classifier_model.pkl` | Random Forest — anomaly type classifier |
| `feature_scaler.pkl` | `StandardScaler` fitted on training data |

If any model fails to load, the UDF continues running but returns `UNKNOWN` for all predictions.

### 3.2 Feature Extraction

For each incoming Kapacitor point, the UDF extracts 20 features from `point.fieldsDouble`:

| Category | Features |
|---|---|
| CPU | `cpu_total_pct`, `cpu_user_pct`, `cpu_system_pct`, `cpu_iowait_pct` |
| Memory | `mem_used_pct`, `swap_used_pct` |
| Disk | `disk_used_pct`, `disk_read_bps`, `disk_write_bps`, `disk_latency_ms`, `disk_iops` |
| Network | `net_in_bps`, `net_out_bps`, `net_err_rate` |
| System | `load1`, `proc_running` |
| Container | `ctr_cpu_total_pct`, `ctr_mem_used_pct_of_limit`, `ctr_unhealthy_count`, `ctr_exited_count` |

Two derived features are computed inside the UDF if not already present on the point:
- `disk_iops` = `(disk_read_bps + disk_write_bps) / 4096`
- `net_err_rate` = `(net_err_in + net_err_out) / (net_in_bps + net_out_bps)`

### 3.3 Inference Pipeline

```
features dict
    │
    ▼
np.array (1 × 20)
    │
    ▼
scaler.transform()          ← StandardScaler (zero-mean, unit-variance)
    │
    ├──▶ anomaly_model.predict / predict_proba   → is_anomaly, anomaly_probability
    ├──▶ failure_model.predict / predict_proba   → failure_within_60min, failure_probability
    └──▶ type_model.predict (if is_anomaly)      → anomaly_type, anomaly_type_name
```

**Anomaly type labels:**

| Type Code | Label |
|---|---|
| 0 | Normal |
| 1 | CPU Spike |
| 2 | Memory Leak |
| 3 | I/O Bottleneck |
| 4 | Network |
| 5 | Container |

> The type classifier is trained on single-fault synthetic scenarios. In production, compound failures (e.g., high CPU causing memory pressure and I/O spikes simultaneously) may be labeled with the nearest matching fault class rather than the exact root cause.

### 3.4 Output Fields

The UDF writes the following fields back onto the point before returning it to Kapacitor:

| Field | Type | Description |
|---|---|---|
| `is_anomaly` | float (0 or 1) | Whether an anomaly was detected |
| `anomaly_probability` | float [0–1] | Anomaly confidence score |
| `failure_within_60min` | float (0 or 1) | Whether failure is predicted within 60 minutes |
| `failure_probability` | float [0–1] | Failure risk score |
| `anomaly_type` | int | Anomaly type code (0–5) |
| `anomaly_type_name` | string | Anomaly type label |
| `alert_level` | string | `NORMAL` / `INFO` / `WARNING` / `CRITICAL` |
| `processing_time_ms` | float | UDF inference latency in milliseconds |

---

## 4. Model Training

The ML models are trained offline using `training/train_ml_models.py` on a synthetic dataset (`tick_synthetic_pm_dataset.csv`) that simulates normal and anomalous system behavior. See [training/README.md](training/README.md) for full details.

After training, copy the four `.pkl` files to the model directory before starting Kapacitor:

```bash
cp anomaly_detector_model.pkl \
   failure_predictor_model.pkl \
   anomaly_type_classifier_model.pkl \
   feature_scaler.pkl \
   /tmp/system_metrics/models/
```

---

## 5. Data Flow Summary

```
Host OS / Docker
      │  (every 1s)
      ▼
  Telegraf
      │  cpu, mem, swap, disk, diskio, net, system, processes, docker
      │  ──▶ InfluxDB: datain / autogen
      │
      ▼
  Kapacitor TICKscript
      │  10 parallel streams, each windowed 10s
      │  derivative() on cumulative counter fields
      │  join(tolerance=30s) → unified feature point
      │
      ▼
  Kapacitor UDF (Python)
      │  StandardScaler → Random Forest / Gradient Boosting inference
      │  anomaly + failure probability + type classification
      │
      ├──▶ InfluxDB: datain / system-anomaly-predictions
      │        (all original metrics + prediction fields)
      │
      └──▶ Kapacitor alert
               INFO  → anomaly detected
               WARN  → failure probability > 60%
               CRIT  → failure probability > 80%
               log: /var/log/kapacitor/system_anomaly_alerts.log
```
