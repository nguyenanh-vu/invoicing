import configparser
import os

from typing import Optional

import constants
import tokens


class Workspace:

    def __init__(self, config : configparser.SectionProxy):

        self.config = config
        self.path = self.edit_path(config.get("folder.workspace", constants.WORKSPACE_FOLDER))

        self.input : str = self.get_sub_path("folder.input", "input")
        self.output : str = self.get_sub_path("folder.output", "output")
        self.model : str = self.get_sub_path("folder.model", "model")
        self.logs : str = self.get_sub_path("folder.logs", "logs")
        self.key : str = self.get_sub_path("folder.key", "key")

        for p in [
            self.input,
            self.output,
            self.model,
            self.logs,
            self.key
        ]:
            os.makedirs(p, exist_ok=True)

    def edit_path(self, path : str) -> str:

        res = path
        res = tokens.DATE.replace_data(self.config.get("format.date", constants.DEFAULT_DATE_FORMAT))
        res = tokens.TODAY.replace_data(self.config.get("format.datetime", constants.DEFAULT_DATETIME_FORMAT))
        res = tokens.TIME.replace_data(self.config.get("format.time", constants.DEFAULT_TIME_FORMAT))

        return res

    def get_sub_path(self, parameter_name : str, default_name : str) -> str:
        return self.edit_path(self.config.get(parameter_name, os.path.join(self.path, default_name)))