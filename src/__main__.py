import argparse
import configparser
import os
import logging
import sys
from typing import List, Optional

import invoicing.constants as constants
import invoicing.orders as orders
import invoicing.input_controller as input_controller
import invoicing.output_controller as output_controller
import invoicing.workspace as workspace
import invoicing.tokens as tokens
import invoicing.__version__ as __version__


DEFAULT_LOGGER = logging.getLogger(constants.APP_NAME)


def main():

    parser = argparse.ArgumentParser(prog=constants.APP_NAME)
    parser.add_argument('-c', '--config', help='path to config file')
    parser.add_argument('-i', '--input', help='name of input', required=True)
    parser.add_argument('-v', '--verbose', help='set console log to INFO', action='store_true')
    parser.add_argument('-d', '--debug', help='set console and file log to DEBUG', action='store_true')
    
    args, _ = parser.parse_known_args()
    debug : bool = args.debug
    verbose : bool = args.verbose

    config_path = os.path.join(constants.CONFIG_FOLDER, 'conf.ini')
    if args.config is not None:
        config_path = args.config
    input_name = args.input

    if not os.path.exists(config_path):
        DEFAULT_LOGGER.exception(FileNotFoundError("configuration file {} not found".format(config_path)))

    config = configparser.ConfigParser()

    try: 
        with open(config_path, 'r') as f:
            config.read_file(f)
    except Exception as e:
        DEFAULT_LOGGER.error("error reading configuration file %s", config_path)
        DEFAULT_LOGGER.error(e, stack_info=True)
        return


    ws : workspace.Workspace
    try: 
        ws = workspace.Workspace(config["DEFAULT"])
    except Exception as e:
        DEFAULT_LOGGER.error("error instantiating workspace")
        DEFAULT_LOGGER.error(e, stack_info=True)
        return

    log_path : str
    try: 
        log_path = setup_logging(config, debug, verbose, ws)
    except Exception as e:
        DEFAULT_LOGGER.error("error setting up logging")
        DEFAULT_LOGGER.error(e, stack_info=True)
        return
    logger = logging.getLogger(constants.APP_NAME)
    logger.info("%s %s started", constants.APP_NAME,  __version__.__version__)
    logger.info("Python version : %s", sys.version)
    logger.info("configuration file path: %s", config_path)
    logger.info("input: %s", input_name)
    logger.info("verbose: %s", str(verbose))
    logger.info("debug: %s", str(debug))
    logger.info("workspace: %s", ws.path)
    logger.info("input folder: %s", ws.input)
    logger.info("output folder: %s", ws.output)
    logger.info("model folder: %s", ws.model)
    logger.info("logs folder: %s", ws.logs)
    logger.info("key folder: %s", ws.key)
    if log_path:
        logger.info("log file in %s", log_path)

    input = input_controller.get_input_controller(input_name, config, ws)

    if input is None:
        raise KeyError("No input configuration present")
    
    outputs = output_controller.get_output_controller(config, ws)
    if len(outputs) == 0:
        raise KeyError("No output configuration present")
    
    res : List[orders.Order] = input.read()

    for order in res:
        for output in outputs:
            try:
                output.save(order, order.order_id, ws.output)
            except Exception as e:
                logger.exception(e)


def setup_logging(config : configparser.ConfigParser,
                  debug : bool, verbose : bool,
                  ws : workspace.Workspace) -> Optional[str]:

    handlers : List[logging.Handler] = []

    datefmt = constants.DEFAULT_LOG_DATE_FORMAT
    fmt : str = constants.DEFAULT_LOG_FORMAT
    console_fmt = constants.DEFAULT_LOG_FORMAT
    console_level = constants.DEFAULT_LOG_CONSOLE_LEVEL
    file_fmt = constants.DEFAULT_LOG_FORMAT
    file_level = constants.DEFAULT_LOG_CONSOLE_LEVEL
    file_path = constants.DEFAULT_LOG_FILEPATH_FORMAT
    file_disabled = False

    if config.has_section("logging"):
        section = config["logging"]
        datefmt = section.get("format.datetime", constants.DEFAULT_LOG_DATE_FORMAT)
        fmt = section.get("format.log", constants.DEFAULT_LOG_FORMAT)
        console_fmt = section.get("console.format", fmt)
        console_level = section.get("console.level", constants.DEFAULT_LOG_CONSOLE_LEVEL)
        file_fmt = section.get("ffile.format", fmt)
        file_level = section.get("file.level", constants.DEFAULT_LOG_FILE_LEVEL)
        file_path = section.get("format.path", constants.DEFAULT_LOG_FILEPATH_FORMAT)
        file_disabled = section.getboolean("file.disabled", False)
    
    if verbose:
        console_level = 'INFO'
    if debug:
        console_level = 'DEBUG'
        file_level = 'DEBUG'

    file_path = tokens.DATE.replace_data(file_path, config['DEFAULT'].get("format.date", constants.DEFAULT_DATE_FORMAT))
    file_path = tokens.TODAY.replace_data(file_path, config['DEFAULT'].get("format.datetime", constants.DEFAULT_DATETIME_FORMAT))
    file_path = tokens.TIME.replace_data(file_path, config['DEFAULT'].get("format.time", constants.DEFAULT_TIME_FORMAT))
    file_path = tokens.APP_NAME.replace_data(file_path)
    file_path = tokens.VERSION.replace_data(file_path)
    
    ch : logging.Handler = logging.StreamHandler(stream=sys.stdout)
    ch.setFormatter( logging.Formatter(fmt = console_fmt, datefmt=datefmt) )
    ch.setLevel(console_level)
    handlers.append(ch)

    if not file_disabled:
        fh : logging.Handler = logging.FileHandler(os.path.join(ws.logs, file_path), 'w', 'utf-8')
        fh.setFormatter( logging.Formatter(fmt = file_fmt, datefmt=datefmt) )
        fh.setLevel(file_level)
        handlers.append(fh)

    logging.basicConfig(
        level=logging.DEBUG,
        format=fmt,
        handlers=handlers
    )

    if file_disabled:
        return None
    else:
        return file_path


if __name__ == "__main__":
    main()
