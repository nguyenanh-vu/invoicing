import os

__currentpath__ : str = os.path.abspath(__file__)
SRC_FOLDER : str = os.path.dirname(__currentpath__)
ROOT_FOLDER : str = os.path.dirname(SRC_FOLDER)
WORKSPACE_FOLDER : str = os.path.join(ROOT_FOLDER, "workspace")
CONFIG_FOLDER : str = os.path.join(WORKSPACE_FOLDER, "conf")