import argparse
import configparser
import os
from typing import List

import constants
import orders
import input_controller
import output_controller
import workspace

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', help='path to config file')
    parser.add_argument('-i', '--input', help='name of input', required=True)
    
    args, _ = parser.parse_known_args()

    config_path = os.path.join(constants.CONFIG_FOLDER, 'conf.ini')
    if args.config is not None:
        config_path = args.config
    input_name = args.input

    if not os.path.exists(config_path):
        raise FileNotFoundError("configuration file {} not found".format(config_path))

    config = configparser.ConfigParser()

    with open(config_path, 'r') as f:
        config.read_file(f)

    ws : workspace.Workspace = workspace.Workspace(config["DEFAULT"])

    input = input_controller.get_input_controller(input_name, config, ws)

    if input is None:
        raise KeyError("No input configuration present")
    
    outputs = output_controller.get_output_controller(config, ws)
    if len(outputs) == 0:
        raise KeyError("No output configuration present")
    
    res : List[orders.Order] = input.read()

    for order in res:
        for output in outputs:
            output.save(order, order.order_id, ws.output)


if __name__ == "__main__":
    main()
