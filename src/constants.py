import os


__currentpath__: str = os.path.abspath(__file__)
APP_NAME = "invoicing"
SRC_FOLDER: str = os.path.dirname(__currentpath__)
ROOT_FOLDER: str = os.path.dirname(SRC_FOLDER)
WORKSPACE_FOLDER: str = os.path.join(ROOT_FOLDER, "workspace")
CONFIG_FOLDER: str = os.path.join(os.path.dirname(os.getcwd()), "workspace", "conf")
DEFAULT_DATETIME_FORMAT: str = "%Y%m%d_%H%M%S"
DEFAULT_DATE_FORMAT: str = "%Y%m%d"
DEFAULT_TIME_FORMAT: str = "%%H%M%S"
DEFAULT_LOG_FORMAT: str = u"%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DEFAULT_LOG_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"
DEFAULT_LOG_FILEPATH_FORMAT: str = "<<TODAY>>.log"
DEFAULT_LOG_CONSOLE_LEVEL: str = 'WARN'
DEFAULT_LOG_FILE_LEVEL: str = 'INFO'
