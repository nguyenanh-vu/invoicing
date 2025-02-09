import os

__currentpath__ : str = os.path.abspath(__file__)
SRC_FOLDER : str = os.path.dirname(__currentpath__)
ROOT_FOLDER : str = os.path.dirname(SRC_FOLDER)
WORKSPACE_FOLDER : str = os.path.join(ROOT_FOLDER, "workspace")
CONFIG_FOLDER : str = os.path.join(os.path.dirname(os.getcwd()), "workspace", "conf")
DEFAULT_DATETIME_FORMAT : str = "%Y%m%d_%H%M%S"
DEFAULT_DATE_FORMAT : str = "%Y%m%d"
DEFAULT_TIME_FORMAT : str = "%%H%M%S"