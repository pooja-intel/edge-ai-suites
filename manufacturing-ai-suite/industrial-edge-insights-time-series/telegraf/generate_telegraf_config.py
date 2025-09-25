#
# Apache v2 license
# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
#

import argparse
import os
import tomlkit
import shutil


# [[inputs.opcua]]
#   ## Metric name
#   name = "opcua"
#   name_override = "wind_turbine_data"
#   endpoint = "$OPCUA_SERVER"
#   log_level = "debug"
#   auth_method = "Anonymous"
#   security_policy = "None"
#   security_mode = "None"
#   [[inputs.opcua.nodes]]
#     name = "grid_active_power"
#     namespace = "1"
#     identifier_type = "i"
#     identifier = "2002"
#     default_tags = { source="opcua_merge" }
#     # default_tags = { tag1 = "value1", tag2 = "value2" }
#   [[inputs.opcua.nodes]]
#     name = "wind_speed"
#     namespace = "1"
#     identifier_type = "i"
#     identifier = "2003"
#     default_tags = { source="opcua_merge" }
#     # default_tags = { tag1 = "value1", tag2 = "value2" }




def main():
    # Create the parser
    parser = argparse.ArgumentParser()

    # Define the arguments
    parser.add_argument("no_of_streams", type=int, help="Number of streams to generate", default=1)
    #parser.add_argument("ingestion_interval", type=str, help="Rate of ingestions like 1s, 100ms, 10ms, etc.,", default="1s")
    #parser.add_argument("config_file", type=str, help="Path of Telegraf config file")
  
    # Parse the arguments
    args = parser.parse_args()
    if args.no_of_streams < 1:
        raise ValueError("Number of streams must be greater than 0")
    dir_path = os.path.join("apps", "wind-turbine-anomaly-detection", "telegraf-config")
    #shutil.copy(dir_path + "/Telegraf.conf", dir_path + "/Telegraf_multi_stream.conf")
    with open(dir_path + "/Telegraf.conf", 'r') as file:
        # Read the content and replace environment variables with placeholders
        content = file.read()
        content = content.replace("$TELEGRAF_METRIC_BATCH_SIZE", "\"placeholder_metric_batch_size\"")  # Replace with a valid placeholder
        content = content.replace("${DEBUG_MODE}", "\"placeholder_debug_mode\"")   # Replace with a valid placeholder

        # Now parse the content with replaced values
        config_data = tomlkit.parse(content)
        stream_name = "opcua"
        del config_data['inputs'][stream_name]
        opc_array = []
        for i in range(1, args.no_of_streams + 1):
            opcua_section = tomlkit.table()
            if args.no_of_streams == 1:
                i = ""
            opcua_section['name'] = f"opcua_stream_{i}"
            opcua_section['name_override'] = "wind-turbine-data"
            opcua_section['endpoint'] = f"opc.tcp://timeseriessoftware-ia-opcua-server-{i}:4840/freeopcua/server/"
            if args.no_of_streams == 1:
                opcua_section['name'] = f"opcua_stream"
                opcua_section['endpoint'] = f"opc.tcp://timeseriessoftware-ia-opcua-server:4840/freeopcua/server/"
            opcua_section['log_level'] = "debug"
            opcua_section['auth_method'] = "Anonymous"
            opcua_section['security_policy'] = "None"
            opcua_section['security_mode'] = "None"

            nodes = []

            node_table1 = tomlkit.table()
            node_table1.add('name', "grid_active_power")
            node_table1.add('namespace', "1")
            node_table1.add('identifier_type', "i")
            node_table1.add('identifier', "2002")
            default_tags1 = tomlkit.inline_table()
            default_tags1["source"] = f"opcua_merge{i}"
            node_table1.add('default_tags', default_tags1)
            nodes.append(node_table1)

            node_table2 = tomlkit.table()
            node_table2.add('name', "wind_speed")
            node_table2.add('namespace', "1")
            node_table2.add('identifier_type', "i")
            node_table2.add('identifier', "2003")
            default_tags2 = tomlkit.inline_table()
            default_tags2["source"] = f"opcua_merge{i}"
            node_table2.add('default_tags', default_tags2)
            nodes.append(node_table2)

            opcua_section['nodes'] = nodes
            opc_array.append(opcua_section)
        config_data['inputs'][stream_name] = opc_array

        # Convert the config back to string
        output_content = tomlkit.dumps(config_data, sort_keys=False)
        
        # Restore the environment variables
        output_content = output_content.replace("\"placeholder_metric_batch_size\"", "$TELEGRAF_METRIC_BATCH_SIZE")
        output_content = output_content.replace("\"placeholder_debug_mode\"", "${DEBUG_MODE}")
        
        # Write the final content with restored environment variables
        with open(dir_path+"/Telegraf_multi_stream.conf", 'w') as file:
            file.write(output_content)

if __name__ == "__main__":
    main()