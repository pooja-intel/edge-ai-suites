#
# Apache v2 license
# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
#
#!/bin/bash -e

SAMPLE_APP="${1:-wind-turbine-anomaly-detection}"
echo "Packaging Helm chart for ${SAMPLE_APP}"
cp -f grafana/dashboards/*.json helm/
cp -f grafana/dashboards/*.yml helm/
cp -f apps/${SAMPLE_APP}/grafana-dashboard/dashboard.json helm/
cp -f influxdb/config/*.conf helm/
cp -f influxdb/init-influxdb.sh helm/
cp -f mqtt-broker/*.conf helm/
cp -f apps/${SAMPLE_APP}/ingestor-data/${SAMPLE_APP}.csv helm/
cp -f apps/${SAMPLE_APP}/telegraf-config/*.conf helm
cp -f grafana/entrypoint.sh helm/grafana_entrypoint.sh
cp -f apps/${SAMPLE_APP}/time-series-analytics-config/config.json helm/
cp -f telegraf/entrypoint.sh helm/telegraf_entrypoint.sh

# Update the Chart.yaml and values.yaml with the SAMPLE_APP name
sed -i "s/name: .*/name: ${SAMPLE_APP}-sample-app/" "helm/Chart.yaml"
sed -i "s/SAMPLE_APP: .*/SAMPLE_APP: ${SAMPLE_APP}/" "helm/values.yaml"
