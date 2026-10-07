# File layout, `.env`, validation, install/Makefile steps (per mode)

## Layout — `multimodal`/`vllm`/`agentic` modes (flat `{{STACK_DIR}}/`)

```
{{STACK_DIR}}/
├── README.md
├── docker-compose.yml
├── .env
├── install.sh                   # HOST_IP, model dl, dataset dl, TLS cert
├── Makefile                     # up/down/status wrapping docker compose; check_env_variables/validate_host_ip targets (optional; sample_*.sh also fine)
├── configs/
│   ├── dlstreamer-pipeline-server/
│   │   ├── config.json          # PIPELINE.md
│   │   ├── pipeline-request-cpu.json
│   │   └── models/              # vision model IR, downloaded by install.sh
│   ├── time-series-analytics-microservice/
│   │   ├── config.json          # TIMESERIES.md
│   │   ├── udfs/<name>.py
│   │   ├── tick_scripts/<name>.tick
│   │   └── models/<name>.pkl
│   ├── telegraf/
│   │   ├── entrypoint.sh
│   │   └── config/Telegraf.conf
│   ├── influxdb/{config,init-influxdb.sh}
│   ├── mqtt-broker/mosquitto.conf
│   ├── grafana/{dashboards_jsons/,provisioning/{dashboards.yml,datasources.yml}}
│   ├── nginx/{nginx.conf,nginx-cert-gen.sh}
│   └── seaweedfs-s3/{seaweedfs_s3_config.json.template,s3-init-buckets.sh}
├── fusion-analytics/
│   ├── Dockerfile
│   ├── fusion.py                # FUSION.md
│   ├── api.py
│   └── requirements.txt
├── <data-simulator-or-adapter>/  # name it for THIS vertical, e.g. {{STACK_DIR}}-simulator/
│   │                             # — never keep the reference's weld-data-simulator/ name;
│   │                             #   swap for real camera+sensor in production
│   ├── Dockerfile
│   ├── publisher.py
│   └── simulation-data/*.avi + *.csv pairs
├── vllm/                          # {{DEPLOYMENT}}=vllm or agentic only — see VLM.md
│   └── vllm-explainer/{Dockerfile,explainer.py,requirements.txt}
├── agentic/                      # {{DEPLOYMENT}}=agentic only — see AGENTIC.md
│   └── docker-compose-agentic.yml + docker-compose-vllm.yml overlays
└── tests/
    ├── conftest.py
    └── test_fusion_pipeline.py  # TESTS.md
```

This is a curated layout, not a mirror of the reference repo — omit
`docker-compose-vllm.yml`/`docker-compose-agentic.yml`/`configs/agentic/`
(unless `{{DEPLOYMENT}}` is `vllm`/`agentic`), `insights-workbench/`,
`ui-service/`, `training/`, `helm/`, vertical-specific `docs/`,
`README-dockerhub.md`, `CHANGELOG.md`, and `third-party-programs.txt` from
the reference — see SKILL.md's *Reference implementation* section for the
full copy/leave-behind table and renaming rule.

## Layout — `ts` mode

See [`APPS_CONVENTION.md`](APPS_CONVENTION.md) for the full `apps/{{APP_NAME}}/`
tree (`simulation-data/`, `telegraf-config/`, `time-series-analytics-config/`,
`grafana-dashboard.json`, `training/`) — this mode adds one folder to an
existing shared repo, it does not generate a new Compose topology.

## `.env` — `multimodal`/`vllm`/`agentic` modes

```
COMPOSE_PROJECT_NAME={{STACK_DIR_SLUG}}
HOST_IP=localhost
GRAFANA_PORT=3000

INFLUXDB_USERNAME=            # alphabets only, >=5 chars, not "admin"
INFLUXDB_PASSWORD=            # >=10 alphanumeric, at least 1 digit, no shell-special chars
VISUALIZER_GRAFANA_USER=      # alphabets only, >=5 chars
VISUALIZER_GRAFANA_PASSWORD=  # same rule as INFLUXDB_PASSWORD
S3_STORAGE_USERNAME=
S3_STORAGE_PASSWORD=
MTX_WEBRTCICESERVERS2_0_USERNAME={{TURN_USER}}
MTX_WEBRTCICESERVERS2_0_PASSWORD=   # generated: openssl rand -hex 16

CONTINUOUS_SIMULATOR_INGESTION=true   # false = ingest once, no loop
SIMULATION_REPLAY_COUNT=3
SIMULATION_TARGET_FPS=10
TS_TOPIC={{SENSOR_MEASUREMENT}}       # topic the simulator/device publishes RAW points to (Telegraf's mqtt_consumer input) — name it TS_TOPIC, matching the reference Compose simulator service's `${TS_TOPIC}` env var verbatim

FUSION_MODE={{FUSION_MODE}}           # AND | OR
TOLERANCE_NS={{TOLERANCE_NS}}         # e.g. 50e6

INFLUXDB_RETENTION_DURATION=1h0m0s
S3_BUCKET_TTL=30m
LOG_LEVEL=INFO

# vllm/agentic modes only:
LLM_MODEL_NAME={{LLM_MODEL_NAME}}
LLM_DEVICE={{LLM_DEVICE}}
LLM_WEIGHT_FORMAT={{LLM_WEIGHT_FORMAT}}
HUGGINGFACEHUB_API_TOKEN=
```

### Env validation rules (`make check_env_variables`/`validate_host_ip`)

| Var | Rule |
|---|---|
| `{{DEPLOYMENT}}` | `vision` \| `ts` \| `multimodal` \| `vllm` \| `agentic` |
| `MODE` | `demo` \| `production` (`vision`/`ts` only) |
| `HOST_IP` | non-empty; reject `127.0.0.1` when validating for remote/WebRTC access |
| `FUSION_MODE` | exactly `AND` or `OR` — reject anything else |
| `TOLERANCE_NS` | numeric (accepts scientific notation e.g. `50e6`), `> 0` |
| `INFLUXDB_USERNAME`/`PASSWORD`, `VISUALIZER_GRAFANA_USER`/`PASSWORD` | non-empty, satisfy the length/charset rules from `.env` comments — reject weak/empty creds before `docker compose up` |
| `PIPELINE_NAME` | matches the DLSPS `config.json` pipeline name exactly |
| `{{VISION_TOPIC}}`, `{{TS_TOPIC}}`, `{{SENSOR_ALERT_TOPIC}}`, `{{FUSION_TOPIC}}` | non-empty, distinct from each other (a collision silently merges two data streams) |
| `MTX_WEBRTCICESERVERS2_0_USERNAME`/`PASSWORD` | non-empty (Coturn auth) |
| `INPUT_TYPE` | `simulator` \| `rtsp` \| `device` \| `opcua` |
| `vllm`/`agentic` only | `LLM_MODEL_NAME` set, `MODEL_PATH` resolvable |
| Vision model file (`configs/dlstreamer-pipeline-server/models/{{DEFAULT_MODEL}}/…`), sensor `.pkl`/`.xml`/`.bin` if the pattern is pretrained | must exist on disk before `up`. This check existing is not a substitute for asking the user up front when the model has no known source — see SKILL.md's *Model availability* rule |

Implement as `check_env_variables`/`validate_host_ip` Makefile targets (no
standalone `validate_env.sh` script — the reference repo doesn't have one),
exiting non-zero with a clear message on first failure; chain both as a
dependency of the `up`/`up_vllm`/`up_agentic` targets, same convention as
`ts` mode's `make check_env_variables`.

### `install.sh` — steps (`multimodal`/`vllm`/`agentic`)

1. **Preflight**: `make check_env_variables` (also `validate_host_ip` when
   validating for remote/WebRTC access).
2. **`.env` population**: `HOST_IP`, generated TURN creds
   (`openssl rand -hex 16`), video/render GIDs for GPU/NPU via
   `getent group video|render` (so DLSPS/UDF containers get `/dev/dri`
   access).
3. **Vision model download**: use `model-download-user` for OMZ/OpenVINO
   models, or fetch the vertical's specific classifier IR from its published
   location. Land it under
   `configs/dlstreamer-pipeline-server/models/{{DEFAULT_MODEL}}/` — a name
   that matches this vertical, never the reference's model directory name.
   **If no local file and no resolvable download URL exist, stop here and
   ask the user for the model instead of writing this step against a path
   that will never be populated.**
4. **Sensor UDF/model**: if the pattern is "pretrained model"
   (`time-series-analytics-user`'s taxonomy), fetch/package the `.pkl` (or
   `.xml`/`.bin`) into `configs/time-series-analytics-microservice/models/`
   under `{{SENSOR_UDF_NAME}}.*`, not the reference's filename; for
   rule-based patterns (threshold/rate-of-change) there is nothing to
   download. Same stop-and-ask rule as step 3 if a pretrained model has no
   known source.
5. **Simulator dataset** (if `{{INPUT_TYPE}}=simulator`): the paired
   `.avi`+`.csv` sample set for this vertical must come from the invoking
   prompt or the user — **do not silently download the reference's
   Intel_Robotic_Welding_Multimodal_Dataset** (that's the weld-defect
   sample's own dataset, not a generic stand-in for every vertical). If no
   local file and no resolvable URL exist, stop here and ask the user for
   one instead of fetching an unrelated dataset, per SKILL.md's *Model
   availability* rule. Once provided, land it under
   `<simulator>/simulation-data/`.
6. **Grafana dashboard swap**: `rm configs/grafana/provisioning/*.json &&
   cp configs/grafana/dashboards_jsons/{{DASHBOARD_SLUG}}.json
   configs/grafana/provisioning/{{DASHBOARD_SLUG}}.json` — dashboards live in
   `dashboards_jsons/` as source-of-truth and get copied into the
   auto-provisioned `provisioning/` directory at install/up time (mirrors the
   reference `Makefile`'s `up:` target).
7. **TLS cert**: generated by Nginx's own entrypoint script
   (`nginx-cert-gen.sh`) on first container start — `install.sh` does not
   need to pre-generate it, just ensure the tmpfs cert volume exists.
8. **Fusion Analytics image**: `docker compose build ia-fusion-analytics` (it
   has no prebuilt registry tag in the reference — always build from
   `fusion-analytics/Dockerfile` unless a registry tag is pinned).
9. **`vllm`/`agentic` only — LLM weights**: run `model-download` ahead of
   `apm-llm` startup; confirm `MODEL_PATH` resolves before marking install
   complete.

### `Makefile` targets (optional, mirrors the reference) — `multimodal`/`vllm`/`agentic`

- `up`: `check_env_variables` → `validate_host_ip` → `down` → dashboard swap →
  `docker compose up -d` — plain `multimodal` mode, no LLM/VLM overlay.
- `up_vllm`: same preflight chain (+ `check_hardware`/`check_models`) plus
  `docker-compose-vllm.yml` — use this one, not `up`, when
  `{{DEPLOYMENT}}=vllm`.
- `up_agentic`: same preflight chain plus `docker-compose-agentic.yml` (which
  itself layers in the vLLM service) — use this one when
  `{{DEPLOYMENT}}=agentic`. Never bring up `vllm`/`agentic` mode by manually
  passing `-f docker-compose-vllm.yml`/`-f docker-compose-agentic.yml` to a
  bare `docker compose up` — these three targets are the actual entry
  points, one per `{{DEPLOYMENT}}` value, not a single conditional `up`.
- `down`: `docker compose down -v --remove-orphans`.
- `status`: `docker ps` table filtered to this stack's network, then tail the
  last 5 log lines of every container and flag any containing `error`
  (case-insensitive) — do not fail the whole command on a false-positive
  first-login Grafana token warning, just surface it.

### Final-summary proof points — `multimodal`/`vllm`/`agentic`

Quote in the closing summary: the `docker compose up -d` output showing all
containers `healthy`/`running`; the three MQTT topic subscriptions
(`{{VISION_TOPIC}}`, `{{TS_TOPIC}}`, `{{FUSION_TOPIC}}`) each with one
captured message; the `FUSION_MODE` value and one example fused-decision JSON
that matches its semantics; the InfluxDB `select * from` output for the
multimodal measurement; the Grafana dashboard URL + confirmation the WebRTC
iframe/panel is present; and, if `{{DEPLOYMENT}}` is `vllm`/`agentic`, the LLM
explanation text for one flagged event.

## `.env` — `ts` mode (required fields, shared across all apps — do not fork per app)

```
COMPOSE_PROJECT_NAME=timeseriessoftware
TIMESERIES_UID=2999
KAPACITOR_PORT=9092
GRAFANA_PORT=3000
LOG_LEVEL=INFO

CONTINUOUS_SIMULATOR_INGESTION=true   # false = ingest once, no loop

INFLUXDB_USERNAME=            # alphabets only, >=5 chars, not "admin"
INFLUXDB_PASSWORD=            # >=10 alphanumeric, at least 1 digit, no shell-special chars
VISUALIZER_GRAFANA_USER=      # alphabets only, >=5 chars
VISUALIZER_GRAFANA_PASSWORD=  # same rule as INFLUXDB_PASSWORD
VISUALIZER_GRAFANA_INACTIVE_TIMEOUT=1h

INFLUXDB_RETENTION_DURATION=1h0m0s
OPCUA_SERVER_PORT_MAPPING=30003
```

No per-vertical topic/mode vars belong in `.env` — those live inside
`apps/{{APP_NAME}}/` (Telegraf input blocks, `config.json`'s `alerts`
section) per [`APPS_CONVENTION.md`](APPS_CONVENTION.md).

### Validation — reuse the Makefile's own target, don't reimplement (`ts`)

```bash
make check_env_variables
```

This already validates `INFLUXDB_USERNAME`/`PASSWORD` and
`VISUALIZER_GRAFANA_USER`/`PASSWORD` against the exact charset/length rules
documented above, and is a hard dependency of both `up_mqtt_ingestion` and
`up_opcua_ingestion` — you never need to call it manually before `make up_*`,
but do call it manually when just scaffolding files (before the first
`make up_*`) to fail fast on a bad `.env`.

Additional rules **this skill** enforces before generating files (not
covered by the Makefile target):

| Var | Rule |
|---|---|
| `{{APP_NAME}}` | kebab-case, not already present in `SAMPLE_APP_LIST` |
| `{{INGEST_TRANSPORT}}` | exactly `opcua` or `mqtt` |
| `{{ALERT_CHANNEL}}` | exactly `mqtt` or `opcua` — never both enabled in the same TICKscript |
| `config.json`/variants | ≤ 5 KB each (microservice hard limit) |
| `{{SENSOR_UDF_NAME}}` | matches the UDF's internal filename inside the packaged `.tar` exactly |

### `Makefile` targets (reference — do not duplicate, just call) — `ts`

- `make up_opcua_ingestion app={{APP_NAME}}` — OPC-UA simulator path;
  MQTT publisher scaled to `0`.
- `make up_mqtt_ingestion app={{APP_NAME}}` — MQTT publisher path; OPC-UA
  simulator scaled to `0`.
- `make status` — table of running containers filtered to this stack +
  a best-effort scan of the last 5 log lines per container for the word
  "error" (informational, not a hard gate — a stale first-login Grafana
  warning is expected noise).
- `make down` — `docker compose down -v --remove-orphans`.

### Final-summary proof points — `ts`

Quote in the closing summary: `{{APP_NAME}}` appearing in the Makefile's
`SAMPLE_APP_LIST` diff; the `make check_env_variables` pass/fail output; the
`make up_{{INGEST_TRANSPORT}}_ingestion app={{APP_NAME}}` container-healthy
output confirming the unused simulator is scaled to `0`; the InfluxDB
`select * from` output for the raw sensor measurement; the flagged-anomaly
log line + the captured MQTT/OPC-UA alert; and the Grafana dashboard URL
with confirmation `apps/{{APP_NAME}}/grafana-dashboard.json` is what's
rendering (not a stale previous app's dashboard).
