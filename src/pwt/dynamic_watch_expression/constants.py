from typing import Literal

from pwt.dynamic_watch_expression import __title__

LOGO = r"""
这里是Logo
这里是Logo
""".strip()
HELP_URL = "https://github.com/PowerWordTree/DDnsGuard"

LOG_ROOT_NAME = __title__
LOG_OUTPUT_DEFAULT = "std"
LOG_OUTPUT_OPTIONS = ("std", "stdout", "stderr")
LOG_OUTPUT_TYPE = Literal["std", "stdout", "stderr"]
LOG_LEVEL_DEFAULT = "WARNING"
LOG_LEVEL_OPTIONS = ("CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG")
LOG_LEVEL_TYPE = Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]
LOG_LEVEL_VERBOSE = "INFO"
LOG_FORMAT_DEFAULT = "{levelname}: {message}"
LOG_DATE_FORMAT_DEFAULT = "%Y-%m-%d %H:%M:%S"
LOG_LEVEL_FILTERS_DEFAULT = None
LOG_NAME_FILTERS_DEFAULT = None
LOG_MSG_FILTERS_DEFAULT = None


WATCHER_NAME_DEFAULT = ""
WATCHER_NAME_FORMAT = "Watcher_{}"
WATCHER_NAME_PATTERN = r"^[a-zA-Z0-9_-]{3,15}$"
WATCHER_INTERVAL_DEFAULT = 120
WATCHER_TOLERANCE_DEFAULT = 0
WATCHER_EXPRESSION_DEFAULT = "fetch_0 & fetch_1 == empty"
WATCHER_EXPRESSION_PATTERN = r"^(?:fetch_\d+|empty|\(|\)|&|\||-|\^|\s)+(?:==|!=|<=|>=|<|>)(?:fetch_\d+|empty|\(|\)|&|\||-|\^|\s)+$"


ACTION_PLUGIN_PATTERN = r"^[a-zA-Z0-9_-]{3,15}$"
ACTION_PLUGIN_FORMATS = (
    "pwt.dynamic_watch_expression.plugins.{}",
    "ddns_guard_plugin_{}",
    "ddns_guard_plugin_{}.plugin",
)
ACTION_TIMEOUT_DEFAULT = 60
ACTION_RETRIES_DEFAULT = 0
ACTION_DELAY_DEFAULT = 1
ACTION_STRATEGY_DEFAULT = "continue"
ACTION_STRATEGY_OPTIONS = ("continue", "success_stop", "failure_stop")
ACTION_STRATEGY_TYPE = Literal["continue", "success_stop", "failure_stop"]
ACTION_NAME_FETCH_FORMAT = "fetch_{}"
ACTION_NAME_EXECUTE_FORMAT = "execute_{}"
