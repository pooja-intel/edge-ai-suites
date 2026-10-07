---
name: manufacturing-app-recipe
description: >-
  Stand up a complete, ready-to-run manufacturing analytics stack on Intel
  hardware with one Docker Compose command, across five deployment shapes:
  vision-only inspection, sensor-only (time-series) anomaly detection,
  vision+sensor multimodal, vision+sensor multimodal with VLM narrative explanation,
  and the same with full agentic orchestration — covering any
  manufacturing-quality vertical (weld defects, CNC tool wear, PCB
  inspection, predictive maintenance, wind-turbine/pump/HVAC monitoring)
  with no glue code. See "When to use this skill" and "Deployment modes" for the full
  component list, trigger conditions, and boundaries.
license: Apache-2.0
compatibility: >-
  Requires Docker + Docker Compose v2, host with Intel CPU (optionally Intel
  GPU/NPU with `video`/`render` groups for GPU-accelerated vision/UDF/LLM
  inference), outbound network access to Docker Hub, ghcr.io, and
  github.com/huggingface.co (for model + sample dataset downloads). Ports
  80/443 (or `${GRAFANA_PORT}`) for the Nginx TLS proxy, plus the Coturn UDP
  port (`multimodal`/`vllm`/`agentic` modes only) and `${OPCUA_SERVER_PORT_MAPPING}`
  (`ts` mode, OPC-UA only) must be free on the host. Tested with the
  open-edge-platform Industrial Edge Insights — Time Series and — Multimodal
  references (manufacturing-ai-suite, v2026.2.0 image tags).
---

# Manufacturing App Recipe — vision / time-series / multimodal / VLM / agentic stacks on Intel hardware

Build a manufacturing quality/monitoring stack on Intel hardware with Docker
Compose, in one of **five deployment modes** (Question 0 picks the shape):

| Mode | Shape | Components added on top of the previous mode |
|---|---|---|
| `vision` | lightweight single vision pipeline (demo/PoC only — no full stack) | DLSPS or a custom GStreamer pipeline |
| `ts` | sensor-only anomaly detection | Telegraf/InfluxDB + Time Series Analytics Microservice (Kapacitor UDF) + Grafana, as a new `apps/<name>/` folder (or a bare UDF in demo mode) |
| `multimodal` | vision + sensor, one fused verdict | DLSPS + the `ts` stack + Fusion Analytics correlator, as a new flat stack directory |
| `vllm` | `multimodal` + narrative explanation | an LLM/VLM (OVMS/vLLM) that explains each fused alert in natural language |
| `agentic` | `vllm` + full agent orchestration | `agent-quality-handler` + `model-download` + (optional) `metrics-manager` microservices orchestrating the VLM layer, instead of a bare OVMS call |

`vllm` and `agentic` **always include the sensor path** — there is no
vision-only or sensor-only VLM/agentic mode; both require the Fusion
Analytics correlator from `multimodal` as their foundation, since the thing being
explained is a **fused** verdict. Follows the open-edge-platform
[Industrial Edge Insights — Time Series](https://github.com/open-edge-platform/edge-ai-suites/tree/main/manufacturing-ai-suite/industrial-edge-insights-time-series)
reference (wind-turbine-anomaly-detection sample, `ts` mode) and
[Industrial Edge Insights — Multimodal](https://github.com/open-edge-platform/edge-ai-suites/tree/main/manufacturing-ai-suite/industrial-edge-insights-multimodal)
reference (weld-defect-detection sample, `multimodal`/`vllm`/`agentic` modes).

## When to use this skill

**Use when** building any manufacturing quality-inspection or sensor-monitoring
pipeline that is one of:

- **`vision`** — a quick local demo/PoC proving a vision model runs on Intel
  hardware, no dashboard/alerting stack.
- **`ts`** — a full deployable sensor-only app (simulator or real OPC-UA/MQTT
  ingest, Kapacitor UDF, MQTT/OPC-UA alerting, Grafana dashboard), or a bare
  UDF prototype against an already-running microservice.
- **`multimodal`** — a camera feed correlated with a sensor stream into **one**
  fused anomaly verdict (AND/OR logic) — weld defect detection, CNC
  tool-wear/vibration correlation, PCB visual + electrical test multimodal.
- **`vllm`** — the `multimodal` stack plus an LLM/VLM that turns each fused verdict
  into a human-readable explanation.
- **`agentic`** — the `vllm` stack plus full agent-orchestration microservices
  (batching, worker agents, metrics) instead of a bare LLM call.

**Not for:** vision-only pipelines that need a **full** end-to-end
dashboard/alerting stack (use `metro-ai-app-recipe` instead — `vision` mode
here is demo/PoC only), non-Intel or cloud-only deployments, or
training/exporting models.

## Supported verticals & use-cases

| Vertical | Vision signal | Sensor signal | Typical mode |
|---|---|---|---|
| Welding / joining | weld-seam defect classification | pressure, gas flow, current | `multimodal`/`vllm`/`agentic` |
| Machining / CNC | tool/surface defect detection | vibration, spindle current | `multimodal`/`vllm`/`agentic` |
| Electronics / PCB | solder-joint/component defect detection | in-circuit test current/voltage | `multimodal`/`vllm`/`agentic` |
| Predictive maintenance | thermal/visual anomaly detection | vibration, temperature, RPM | `multimodal`/`vllm`/`agentic` or `ts`-only |
| Renewable energy | — | wind speed, grid active power | `ts` |
| Rotating machinery | — | vibration, RPM, current | `ts` |
| HVAC / facilities | — | temperature, energy draw, airflow | `ts` |
| Process / utilities | — | pressure, flow, level | `ts` |
| Camera-only inspection, quick PoC | any OpenVINO IR / ONNX classifier or detector | — | `vision` |
| Custom | any OpenVINO IR / ONNX classifier or detector | any scikit-learn model or rule via UDF | any mode |

The invoking prompt maps its vertical to concrete `{{OBJECT}}`,
`{{APP_NAME}}`/`{{STACK_DIR}}`, `{{DEFAULT_MODEL}}`, `{{SENSOR_UDF_NAME}}`,
`{{DASHBOARD_SLUG}}`/`{{DASHBOARD_TITLE}}` — nothing else changes.

## How to use this skill

1. Read this file end-to-end.
2. Ask **Question 0 (deployment mode)** first — `vision` \| `ts` \| `multimodal` \|
   `vllm` \| `agentic`. No default; the five modes build materially different
   artifacts, so always confirm explicitly rather than guessing.
3. Branch into the mode-specific question set (below) in ONE batched message
   (defaults in brackets); accept `go`/`defaults`/empty.
4. Run parameter validation (below); refuse to proceed on any failure.
5. Load reference file(s) on demand per the mode's row in *Reference files* —
   **not all up front**.
6. Verify against the mode's completion criteria before declaring success;
   `make check_env_variables` is **step 0** of install/`make up_*`.

## Reference files (load on demand)

| File | Load for mode(s) | When authoring |
|---|---|---|
| [`references/DEMO_POC.md`](references/DEMO_POC.md) | `vision`, `ts` (demo sub-path) | lightweight single-component path — no full stack |
| [`references/PIPELINE.md`](references/PIPELINE.md) | `vision`, `multimodal`, `vllm`, `agentic` | DLSPS `config.json` (RTSP source, classification/detection, S3 frame write, WebRTC, MQTT metadata), GPU/NPU variants |
| [`references/INGEST.md`](references/INGEST.md) | `ts` | OPC-UA/MQTT simulator choice, Telegraf wiring, real-device connection |
| [`references/APPS_CONVENTION.md`](references/APPS_CONVENTION.md) | `ts` | the `apps/<name>/` scaffold, Makefile `SAMPLE_APP_LIST` registration |
| [`references/ANALYTICS.md`](references/ANALYTICS.md) | `ts` | Time Series Analytics Microservice `config.json` variants (streaming/batch/OPC-UA-alert) for the standalone `apps/<name>/` shape |
| [`references/TIMESERIES.md`](references/TIMESERIES.md) | `multimodal`, `vllm`, `agentic` | Telegraf MQTT→InfluxDB ingestion + Time Series Analytics Microservice wiring inside the flat multimodal-stack shape (delegates UDF pattern choice to `time-series-analytics-user`) |
| [`references/FUSION.md`](references/FUSION.md) | `multimodal`, `vllm`, `agentic` | Fusion Analytics service (MQTT correlate-by-timestamp, AND/OR logic, InfluxDB write) — **always load for these three modes**, the core differentiator |
| [`references/VLM.md`](references/VLM.md) | `vllm`, `agentic` | the bare LLM/VLM narrative-explanation layer (OVMS/vLLM call over a fused-alert batch) — **always load for these two modes** |
| [`references/AGENTIC.md`](references/AGENTIC.md) | `agentic` only | the agent-orchestration overlay (`agent-quality-handler` + `model-download` + optional `metrics-manager`) on top of `VLM.md`'s bare LLM call |
| [`references/PROXY_UI.md`](references/PROXY_UI.md) | all production modes | `nginx.conf` proxy, Grafana dashboard provisioning, Mosquitto, (multimodal+ family) SeaweedFS S3 |
| [`references/INSTALL.md`](references/INSTALL.md) | all production modes | file layout, `.env`, validation rules, `install.sh`/Makefile targets per mode |
| [`references/TESTS.md`](references/TESTS.md) | all production modes | `conftest.py`, per-mode assertion contracts |

## Parameters (from invoking prompt)

| Param | Purpose | Modes |
|---|---|---|
| `{{DEPLOYMENT}}` | `vision` \| `ts` \| `multimodal` \| `vllm` \| `agentic` — Question 0's answer | all |
| `{{MODE}}` | `demo` \| `production` (default `production`) — sub-mode within `vision`/`ts`; `multimodal`/`vllm`/`agentic` are production-only | `vision`, `ts` |
| `{{OBJECT}}` | defect/anomaly label in dashboard/alerts (e.g. `weld_defect`, `tool_wear`, `wind_turbine`); any MQTT/Grafana/InfluxDB-safe string | all |
| `{{STACK_DIR}}` | absolute parent path for a new, flat, standalone stack directory (e.g. `weld-defect-stack`) — `multimodal`/`vllm`/`agentic` only; never assumed from the current working directory | `multimodal`, `vllm`, `agentic` |
| `{{TS_REPO_DIR}}` | absolute path to an existing `industrial-edge-insights-time-series` checkout to add `apps/{{APP_NAME}}/` into (or where to clone it fresh) — `ts` production only | `ts` |
| `{{APP_NAME}}` | the new `apps/<name>/` folder name, kebab-case (e.g. `wind-turbine-anomaly-detection`) | `ts` |
| `{{DEFAULT_MODEL}}`, `{{OTHER_MODELS}}` | vision classifier/detector options for DLSPS | `vision`, `multimodal`, `vllm`, `agentic` |
| `{{PIPELINE_NAME}}` | canonical DLSPS pipeline `name` (e.g. `weld_defect_classification`); variants `<name>`/`_gpu`/`_npu` | `vision`, `multimodal`, `vllm`, `agentic` |
| `{{VISION_TOPIC}}` | MQTT topic DLSPS publishes classification/detection metadata to | `multimodal`, `vllm`, `agentic` |
| `{{SENSOR_UDF_NAME}}` | Time Series Analytics UDF name; backed by a pretrained model or a threshold/rate-of-change rule ([time-series-analytics-user](../time-series-analytics-user/references/patterns.md) patterns) | `ts`, `multimodal`, `vllm`, `agentic` |
| `{{SENSOR_MEASUREMENT}}` | InfluxDB measurement / MQTT topic the raw sensor stream lands on | `ts`, `multimodal`, `vllm`, `agentic` |
| `{{SENSOR_TAGS}}` | OPC-UA node IDs / MQTT field names to ingest | `ts` |
| `{{INGEST_TRANSPORT}}` | `opcua` \| `mqtt` (default `opcua` for `ts`) — which simulator/Telegraf input plugin drives ingestion | `ts`, `multimodal`, `vllm`, `agentic` |
| `{{TS_TOPIC}}` | MQTT topic the Time Series Analytics UDF publishes **every** flagged point to | `multimodal`, `vllm`, `agentic` |
| `{{SENSOR_ALERT_TOPIC}}` | MQTT topic for the sensor-only crit alert | `multimodal`, `vllm`, `agentic` |
| `{{ALERT_CHANNEL}}` | `mqtt` (default) \| `opcua` — **enable only one** | `ts` |
| `{{ALERT_TOPIC}}` | MQTT topic for crit alerts, only when `{{ALERT_CHANNEL}}=mqtt` | `ts` |
| `{{FUSION_TOPIC}}` | MQTT topic Fusion Analytics publishes the fused verdict to | `multimodal`, `vllm`, `agentic` |
| `{{FUSION_MODE}}` | `AND` \| `OR` (default `OR`) — both vs either modality must flag anomaly | `multimodal`, `vllm`, `agentic` |
| `{{TOLERANCE_NS}}` | timestamp-matching tolerance in nanoseconds (default `50e6` = 50 ms) | `multimodal`, `vllm`, `agentic` |
| `{{DASHBOARD_SLUG}}` / `{{DASHBOARD_TITLE}}` | Grafana dashboard identifier | all production modes |
| `{{INPUT_TYPE}}` | `simulator` (default) \| `rtsp`/`device` (real camera) + `mqtt`/`opcua` (real sensor feed) | `vision`, `multimodal`, `vllm`, `agentic` |
| `{{LLM_MODEL_NAME}}`, `{{LLM_DEVICE}}`, `{{LLM_WEIGHT_FORMAT}}` | VLM/LLM model + device + OpenVINO weight format | `vllm`, `agentic` |
| `{{BATCH_TRIGGER_MODE}}`, `{{BATCH_SIZE}}`/`{{BATCH_INTERVAL_S}}` | `size` (default, `{{BATCH_SIZE}}=10`) \| `time` (`{{BATCH_INTERVAL_S}}=30`) — when Fusion Analytics flushes its `batch-complete` MQTT event | `vllm`, `agentic` |
| `{{AGENT_METRICS}}` | `yes` \| `no` (default `no`) — include the optional `metrics-manager`/Prometheus overlay | `agentic` |
| `{{HOST_IP}}` | host IP for Nginx/Grafana/WebRTC (default `localhost`) | all production modes |
| `{{TURN_USER}}`, `{{TURN_PASS}}` | Coturn / MediaMTX ICE credentials (default `turnuser` / a generated secret) | `multimodal`, `vllm`, `agentic` |

## Questions (single batched prompt, per mode)

**Question 0 — Deployment mode** (no default, ask explicitly): `vision` \|
`ts` \| `multimodal` \| `vllm` \| `agentic` — see the *Deployment modes* table
above. Then ask ONLY the questions for the chosen mode:

### `vision` mode

0b. Demo sub-path: a DL Streamer/GStreamer pipeline (`dlstreamer-coding-agent`)
    or a REST-driven DLSPS instance (`dlsps-user`)? No default — the two
    produce unrelated artifacts.
1. Vision model [`{{DEFAULT_MODEL}}`] (also: `{{OTHER_MODELS}}`)
2. Vision device [CPU] (GPU, NPU, AUTO)
3. Video input [sample video] (or RTSP URL / `/dev/videoN` / local path)

Full guidance in [`references/DEMO_POC.md`](references/DEMO_POC.md) —
*Vision-only* section.

### `ts` mode

0b. Sub-mode [`production`]: `demo` (bare UDF, no scaffold — STOP and
    delegate entirely to `time-series-analytics-user`, skip questions below)
    or `production` (full `apps/<name>/` stack).

Production questions:

1. **Working directory** — the absolute path to an existing
   `industrial-edge-insights-time-series` checkout to add
   `apps/{{APP_NAME}}/` into (must already contain `docker-compose.yml` +
   `Makefile` + `apps/` at its root), or where to clone the reference repo
   fresh if none exists. Never guess a path or default to the current
   working directory.
2. App name [`{{APP_NAME}}`] — new `apps/<name>/` folder to create
3. Sensor pattern [pretrained model] (threshold, rate-of-change, rolling
   z-score, pretrained model — see `time-series-analytics-user`
   `references/patterns.md`) + `{{SENSOR_TAGS}}`
4. Ingestion transport [`opcua`] (or `mqtt`) — drives which simulator/Telegraf
   input plugin is used
5. Real device or simulator? [simulator with a sample CSV] (or a real
   OPC-UA server URL / MQTT broker to connect Telegraf to directly)
6. Alert channel [`mqtt`, `{{ALERT_TOPIC}}`] (or `opcua`) — **enable only one**
7. Dashboard title [`{{DASHBOARD_TITLE}}`]

### `multimodal` mode (and the shared base for `vllm`/`agentic`)

1. **Working directory** — the absolute parent path to create
   `{{STACK_DIR}}/` in. A **new, flat, standalone** stack directory, not a
   folder inside an existing repo checkout — confirm explicitly.
2. Vision model [`{{DEFAULT_MODEL}}`] (also: `{{OTHER_MODELS}}`) — classifier
   or detector
3. Vision device [CPU] (GPU, NPU, AUTO)
4. Video input [simulator sample video] (or RTSP URL / `/dev/videoN` / local
   path); sets DLSPS source
5. Sensor pattern [pretrained model] (threshold, rate-of-change, rolling
   z-score, pretrained model — see `time-series-analytics-user`
   `references/patterns.md`)
6. Sensor input [simulator sample CSV] (or MQTT/OPC UA live feed); sets
   Telegraf `TELEGRAF_INPUT_PLUGIN`
7. Multimodal mode [`{{FUSION_MODE}}`, default `OR`] + `{{TOLERANCE_NS}}`
   [default `50e6`]
8. Alert channels [MQTT `{{SENSOR_ALERT_TOPIC}}` + `{{FUSION_TOPIC}}`]
9. Dashboard slug [`{{DASHBOARD_SLUG}}`]

### `vllm` mode

Ask the 9 `multimodal`-mode questions above, **plus**:

10. LLM/VLM model [none — must be named, OMZ/HF, or a local path] +
    `{{LLM_DEVICE}}` [GPU] + `{{LLM_WEIGHT_FORMAT}}` [int4] — or
    `LLM_MODE=fallback` for a rule-based templated explanation with no live
    model.
11. Batch trigger for the explanation layer [`{{BATCH_TRIGGER_MODE}}=size`,
    `{{BATCH_SIZE}}=10`] (or `time`, `{{BATCH_INTERVAL_S}}=30`) — Fusion
    Analytics flushes a `batch-complete` MQTT event on this trigger; never
    leave it unset (see FUSION.md's *Batching for the explanation layer*).

### `agentic` mode

Ask the 11 `vllm`-mode questions above, **plus**:

12. Include the optional `metrics-manager`/Prometheus overlay for
    LLM-usage/latency metrics? [`{{AGENT_METRICS}}`, default `no`]

## Parameter validation (enforce BEFORE install/`make up_*` runs)

Confirm the **working directory** (`{{STACK_DIR}}` or `{{TS_REPO_DIR}}`) is
where the user actually wants files created — never fall back to the current
working directory or a temp path. Reuse `make check_env_variables`/
`validate_host_ip` (all production modes) as step 0; reject on any failure.
Full validation rules tables (per mode) are in
[`references/INSTALL.md`](references/INSTALL.md).

## Reference architecture

- **`vision`** — single DLSPS/GStreamer pipeline, no dashboard. See
  [`references/DEMO_POC.md`](references/DEMO_POC.md).
- **`ts`** — sensor/simulator → Telegraf (OPC-UA or MQTT input) → InfluxDB
  (storage) + Time Series Analytics Microservice (Kapacitor UDF) →
  MQTT/OPC-UA alert → Grafana, behind an Nginx TLS proxy. See
  [`references/INGEST.md`](references/INGEST.md) /
  [`references/ANALYTICS.md`](references/ANALYTICS.md).
- **`multimodal`** — two paths meeting in Fusion Analytics: **vision**
  DLSPS→MQTT, and **sensor** simulator/device→MQTT→Telegraf→InfluxDB +
  MQTT→Time Series Analytics Microservice (Kapacitor UDF)→MQTT; Fusion
  Analytics correlates both MQTT streams by timestamp and writes the fused
  verdict to InfluxDB + MQTT. See [`references/FUSION.md`](references/FUSION.md).
- **`vllm`** — `multimodal`, plus an LLM/VLM (OVMS/vLLM) subscribing to a
  fused-alert batch and publishing a narrative explanation. See
  [`references/VLM.md`](references/VLM.md).
- **`agentic`** — `vllm`, plus `agent-quality-handler` orchestrating the LLM
  call via LangGraph worker agents, `model-download` fetching/converting the
  LLM weights ahead of time, and (optionally) `metrics-manager`. See
  [`references/AGENTIC.md`](references/AGENTIC.md).

## Images — pin to the latest available tag (never `:latest`)

Resolve each image to the **newest published stable tag on Docker Hub**
(query the repo's `tags` API with `ordering=last_updated`), pin it, and
ignore `*-weekly` pre-releases.

- `intel/dlstreamer-pipeline-server:2026.2.0-ubuntu24` (vision — `vision`,
  `multimodal`, `vllm`, `agentic`)
- `intel/ia-time-series-analytics-microservice:<latest>` (Kapacitor + UDF —
  `ts`, `multimodal`, `vllm`, `agentic`)
- `intel/ia-multimodal-fusion-analytics:<latest>` (multimodal correlator, built
  from `fusion-analytics/Dockerfile` if no prebuilt tag is pinned yet —
  `multimodal`, `vllm`, `agentic`)
- `telegraf:1.39.3-alpine`, `influxdb:1.12.4` (all production modes)
- `eclipse-mosquitto:2.0.22`, `grafana/grafana-oss:13.0.2`, `nginx:1.31.4`
  (all production modes)
- `bluenviron/mediamtx:1.20.1` (WebRTC WHIP/WHEP), `coturn/coturn:4.17.2-alpine`
  (ICE/TURN), `chrislusf/seaweedfs:4.42` (S3) — `multimodal`, `vllm`, `agentic` only
- `intel/ia-opcua-server:<latest>` / `intel/ia-mqtt-publisher:<latest>`
  (simulators) — `ts` only, whichever matches `{{INGEST_TRANSPORT}}`
- `openvino/model_server:<gpu-tag>` (OVMS, serves the LLM/VLM) — `vllm`,
  `agentic` only
- Agentic-only: `intel/agent-quality-handler`, `intel/model-download`,
  `intel/metrics-manager` (only if `{{AGENT_METRICS}}=yes`) — `agentic` only

## Layout — per mode

- **`vision`** — no fixed layout; whatever `dlstreamer-coding-agent`/
  `dlsps-user` produces for a single pipeline.
- **`ts`** — a new `apps/{{APP_NAME}}/` folder inside the existing generic
  Time Series AI Stack repo (shared `docker-compose.yml`/`Makefile`/`configs/`
  at the repo root): `simulation-data/`, `telegraf-config/`,
  `time-series-analytics-config/{config.json,udfs/,tick_scripts/,models/}`,
  `grafana-dashboard.json`, `training/`. Full annotated tree in
  [`references/APPS_CONVENTION.md`](references/APPS_CONVENTION.md).
- **`multimodal`/`vllm`/`agentic`** — a flat, new `{{STACK_DIR}}/`: `README.md`,
  `docker-compose.yml`, `.env`, `install.sh`, `Makefile` (with
  `check_env_variables`/`validate_host_ip` targets, no standalone validation
  script),
  `configs/` (`dlstreamer-pipeline-server/`,
  `time-series-analytics-microservice/`, `telegraf/`, `influxdb/`,
  `mqtt-broker/`, `grafana/`, `nginx/`, `seaweedfs-s3/`), `fusion-analytics/`,
  a data simulator/adapter, `tests/`, plus (for `vllm`/`agentic`) an
  `agentic/` or `vllm/` overlay directory for the LLM service and (`agentic`
  only) the agent-orchestration services. Full annotated tree in
  [`references/INSTALL.md`](references/INSTALL.md). Name the data simulator
  directory for **this** vertical (e.g. `{{STACK_DIR}}-simulator/`) — never
  keep the reference's `weld-data-simulator/` name in a stack for a
  different vertical; see *Reference implementation* below for the full
  renaming/pruning rule.

## Template variable substitution

Every `{{VAR}}` MUST be substituted with its concrete value BEFORE writing
the file — a literal `{{...}}` left in `nginx.conf`, `config.json`,
`Telegraf.conf`, `fusion.py`, a dashboard JSON, or a test file is a syntax
error.

## Execution guardrails

- Hard timeouts: model dl 300 s; simulator dataset dl 120 s; `compose pull`
  300 s; `compose up -d` 120 s + 180 s healthy; each pytest 60 s.
- Max 2 retries per step, then STOP and print last 30 log lines from the
  failing container. Never loop.
- Before `compose up` (`multimodal`/`vllm`/`agentic`): confirm the Nginx TLS port
  and Coturn UDP port are free on the host. (`ts`): confirm `${GRAFANA_PORT}`
  and, if OPC-UA, `${OPCUA_SERVER_PORT_MAPPING}` are free.
- **Bypass host proxy for localhost/LAN curl, but don't blanket-disable TLS
  verification** — every curl MUST use `--noproxy '*'`. `-k` is only safe for
  the literal `https://localhost/...` bootstrap check (self-signed cert, no
  network path for a MITM); for anything hitting a real `${HOST_IP}`/LAN
  address, extract the generated cert instead (`docker cp <nginx-container>:
  /opt/nginx/certs/cert.pem ./nginx-cert.pem`) and use `--cacert
  ./nginx-cert.pem --resolve ${HOST_IP}:${GRAFANA_PORT}:127.0.0.1` (the cert
  is `CN=localhost` with no SAN, so `--resolve` is required for hostname
  verification to match) — never fall back to `-k` on a non-localhost target.
- `multimodal`/`vllm`/`agentic`: test multimodal end-to-end via MQTT, not just REST
  200s — confirm `{{VISION_TOPIC}}`, `{{TS_TOPIC}}`, `{{FUSION_TOPIC}}` all
  appear on the broker.
- **Known startup-order caveat** (`multimodal`/`vllm`/`agentic`): Fusion Analytics
  only starts fusing once the vision metadata carries an RTP sender
  timestamp — DLSPS may not emit that for its first ~300 packets, so allow a
  short warm-up delay before asserting fused output in tests.
- `ts`: only one of `ia-opcua-server`/`ia-mqtt-publisher` runs at a time —
  verify the unused simulator is scaled to `0`, not merely stopped.
- `ts`: **enable only one alert channel** — MQTT and OPC-UA alert blocks in
  the same TICKscript is unsupported.
- `ts`: `config.json` (and variants) **MUST stay ≤ 5 KB**.
- pytest venv at `./.venv` inside the stack/repo dir (`python -m venv .venv`)
  — system pip is PEP-668 blocked; `/tmp` may be `noexec`.
- **Never fabricate a missing pretrained model** (vision or sensor) — if no
  existing file or resolvable download/training source is available, stop
  and ask the user instead of shipping an empty placeholder path (see
  *Model availability* below).

## Model availability — ask, don't fabricate

`{{DEFAULT_MODEL}}` (vision, all non-`ts` modes) and, if the sensor pattern
is "pretrained model", `{{SENSOR_UDF_NAME}}`'s `.pkl`/`.xml`/`.bin` must be
either already available locally (a real path the invoking prompt names), or
fetchable from a concrete, resolvable URL (OMZ/OpenVINO Model Zoo, Hugging
Face, or a URL the invoking prompt supplied) via `model-download-user`/
`install.sh`. The same rule applies to `{{LLM_MODEL_NAME}}` in `vllm`/`agentic`
mode. If neither is true, **stop before writing the model-download step and
ask the user to provide the model** — do not invent a plausible-looking
model directory/filename and leave it as an empty placeholder.

## Optional external skills

If available, invoke; otherwise write files from the reference templates.

- `dlsps-user` — DLSPS deploy/config/REST for the vision half ([PIPELINE](references/PIPELINE.md))
- `dlstreamer-coding-agent` — custom GStreamer pipeline authoring (+ `vision`-mode demo/PoC app)
- `time-series-analytics-user` — sensor UDF + TICKscript authoring/deploy
  ([ANALYTICS](references/ANALYTICS.md) for `ts`, [TIMESERIES](references/TIMESERIES.md)
  for `multimodal`/`vllm`/`agentic`) — the primary delegate for `ts` demo mode
- `model-download-user` — OMZ/OpenVINO model IR for the vision model, or LLM
  weights for `vllm`/`agentic`
- No delegate skill exists yet for the **Fusion Analytics** correlator or the
  bare **VLM narrative-explanation** call — author them from
  [`references/FUSION.md`](references/FUSION.md) /
  [`references/VLM.md`](references/VLM.md)

## Reference implementation — a template to read, not a folder to clone

The upstream
[`industrial-edge-insights-time-series/`](https://github.com/open-edge-platform/edge-ai-suites/tree/main/manufacturing-ai-suite/industrial-edge-insights-time-series)
wind-turbine-anomaly-detection sample (`ts` mode) and
[`industrial-edge-insights-multimodal/`](https://github.com/open-edge-platform/edge-ai-suites/tree/main/manufacturing-ai-suite/industrial-edge-insights-multimodal)
weld-defect-detection sample (`multimodal`/`vllm`/`agentic` modes) are the
**shape reference** — read them to learn the structure, then **author the
new stack's files with vertical-specific names and content**. Do **not**
`cp -r` either reference repo and patch it in place — that leaves
vertical-specific leftovers (unused `weld_anomaly_detector.*` files, a
`weld-data-simulator/` folder for a non-weld vertical, weld training
scripts, weld docs) sitting in a stack that has nothing to do with that
vertical, and is the single most common mistake when using this skill.

### What to copy vs. what to leave behind (`multimodal`/`vllm`/`agentic`)

| Copy (adapt names/content to `{{OBJECT}}`/`{{SENSOR_UDF_NAME}}`/`{{STACK_DIR}}`) | Leave out unless the mode/question explicitly requests it |
|---|---|
| `docker-compose.yml` topology, `.env` keys, `Makefile`/`sample_*.sh` targets | `docker-compose-vllm.yml`/`docker-compose-agentic.yml`/`configs/agentic/` — `vllm`/`agentic` modes only |
| `configs/{dlstreamer-pipeline-server,time-series-analytics-microservice,telegraf,influxdb,mqtt-broker,grafana,nginx,seaweedfs-s3}/` structure | `insights-workbench/`, `ui-service/` — weld-specific VLM/agentic UI, not part of the base multimodal stack |
| `fusion-analytics/{Dockerfile,fusion.py,api.py,requirements.txt}` (generalize label lists — see [FUSION.md](references/FUSION.md)) | `training/` (weld classifier/VLM training scripts) — the new vertical's model is supplied by the user or fetched via `model-download-user`, not trained here |
| the data simulator's `Dockerfile`/`publisher.py` control flow (paired video+CSV replay) | `docs/user-guide/weld-defect-detection/`, `README-dockerhub.md`, `CHANGELOG.md`, `third-party-programs.txt` — reference-repo metadata |
| one dashboard JSON as a layout template | the reference's other dashboard variants (`*_agentic.json`, `*_vlm.json`) unless `{{DEPLOYMENT}}` is `vllm`/`agentic` |
| `tests/` structure/pattern from [TESTS.md](references/TESTS.md) | the reference's actual weld-assertion test bodies — write new assertions against `{{VISION_TOPIC}}`/`{{TS_TOPIC}}`/`{{FUSION_TOPIC}}` |
| `helm/` | always — Helm/Kubernetes deployment is out of scope for this skill; Docker Compose only |

### What to copy vs. what to leave behind (`ts`)

| Copy | Leave out |
|---|---|
| `simulation-data/`, `telegraf-config/`, `time-series-analytics-config/` shape, `grafana-dashboard.json` | another app's `training/` scripts — write new ones only if this vertical trains a model |
| the chosen simulator's control flow (OPC-UA server or MQTT publisher) | the unused simulator (OPC-UA vs MQTT) entirely |
| `Makefile` `SAMPLE_APP_LIST` registration pattern | `DEFAULT_SAMPLE_APP` change, unless explicitly requested |

### Renaming rule — no leftover vertical-specific names

Every file, directory, service name, container name, image env var, MQTT
topic, InfluxDB measurement, WebRTC peer-id, and dashboard filename that is
vertical-specific in a reference (contains `weld`/`Weld`, `wind-turbine`, or
any other old vertical's name) MUST be renamed to match this stack's own
`{{OBJECT}}`/`{{SENSOR_UDF_NAME}}`/`{{STACK_DIR}}`/`{{APP_NAME}}` — never
leave the reference's naming in a generated stack for a different vertical
(data simulator directory + Compose service, its image env var, UDF
file/class + tick script — **delete** the reference's original files
entirely rather than leaving them unused alongside the new ones, pretrained
model files, vision model directory, WebRTC `peer-id`/S3 `folder_prefix`,
MQTT topics, InfluxDB measurements, dashboard JSON filename).

## Completion criteria (per mode, all applicable must pass)

**`vision`** (demo/PoC — see [`references/DEMO_POC.md`](references/DEMO_POC.md)):
1. The chosen delegate skill's container(s) start successfully.
2. One inference call round-trips end-to-end with evidence quoted verbatim.
3. No literal `{{...}}` remains.

**`ts`** (demo — same bar as `time-series-analytics-user`; production — all
of these):
1. `apps/{{APP_NAME}}/` exists with all required subpaths; registered in
   `SAMPLE_APP_LIST`.
2. `make check_env_variables` exits 0 with a valid `.env`.
3. `make up_{{INGEST_TRANSPORT}}_ingestion app={{APP_NAME}}` → all
   containers `running`/`healthy`; unused simulator scaled to `0`.
4. `curl -k --noproxy '*' https://<HOST_IP>:${GRAFANA_PORT}/ts-api/kapacitor/v1/ping` returns 204/200 (`-k` only valid when `{{HOST_IP}}=localhost`; otherwise use `--cacert`/`--resolve` per *Execution guardrails*).
5. InfluxDB measurement for the raw sensor stream populated within 30 s.
6. `config.json`'s `udfs.models` key consistent with the chosen UDF pattern.
7. The UDF-flagged measurement populates; the alert channel captures one
   crit alert.
8. Grafana shows `apps/{{APP_NAME}}/grafana-dashboard.json` rendering live
   data.
9. `pytest -q tests/` passes, ≥ 6 tests collected.

**`multimodal`** (all of these; **`vllm`/`agentic` add their own criteria below**):
1. `./install.sh` succeeds; no leftover reference-vertical artifacts.
2. `make check_env_variables` exits 0; an invalid `FUSION_MODE` exits non-zero.
3. `docker compose up -d` → all containers `running`/`healthy` (incl.
   `mediamtx`, `coturn`, `seaweedfs-*`).
4. All three MQTT topics (`{{VISION_TOPIC}}`, `{{TS_TOPIC}}`,
   `{{FUSION_TOPIC}}`) carry data.
5. A fused message appears only per `{{FUSION_MODE}}` semantics, within
   `{{TOLERANCE_NS}}`.
6. InfluxDB has both the raw vision measurement and the multimodal measurement
   populated.
7. Grafana renders the WebRTC panel + sensor trend + multimodal verdict table.
8. `pytest -q tests/` passes, ≥ 9 tests collected.
9. No literal `{{...}}` remains anywhere.

**`vllm`** (criteria 1–9 above, plus):
10. The LLM/VLM service (OVMS/vLLM) health check passes before it is marked
    ready.
11. Publishing a synthetic fused-alert batch produces one explanation output,
    quoted verbatim in the final summary.
12. `LLM_MODE=fallback` (if selected) still produces a structured explanation
    with no LLM running.

**`agentic`** (criteria 1–12 above, plus):
13. `model-download` completes and `apm-llm`'s health check passes
    (`GET /v3/config` returns 200) before `apm-agent` is marked healthy.
14. Publishing a synthetic `apm/batch-complete` MQTT event produces one
    agent-orchestrated explanation in `apm-agent`'s `OUTPUT_DIR`, quoted
    verbatim.
15. If `{{AGENT_METRICS}}=yes`: `metrics-manager`/Prometheus reports at
    least one LLM-latency metric.

## Final summary — surface the proof (don't just name files)

Graders see only your **final message** + tool *names*, not file contents.
An expectation counts as met only if you **state it and quote the one
decisive line** in your closing summary — walk every completion criterion
for the chosen `{{DEPLOYMENT}}` mode plus the proof-point checklist in
[`references/INSTALL.md`](references/INSTALL.md) → *Final-summary proof
points*. A claim with no quoted evidence is treated as unmet.
