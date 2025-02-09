import configparser
import os

from typing import Optional

import constants


class Workspace:

    def __init__(self, config : configparser.SectionProxy):

        self.path = config.get("folder.workspace", constants.WORKSPACE_FOLDER)

        self.input : str = config.get("folder.input", os.path.join(self.path, "input"))
        self.output : str = config.get("folder.output", os.path.join(self.path, "output"))
        self.model : str = config.get("folder.model", os.path.join(self.path, "model"))
        self.logs : str = config.get("folder.logs", os.path.join(self.path, "logs"))
        self.key : str = config.get("folder.key", os.path.join(self.path, "key"))

        for p in [
            self.input,
            self.output,
            self.model,
            self.logs,
            self.key
        ]:
            os.makedirs(p, exist_ok=True)
