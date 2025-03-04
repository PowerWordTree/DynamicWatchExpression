from typing import Literal

from pwt.dynamic_watch_expression import __title__

LOGO = r"""
这里是Logo
这里是Logo
""".strip()
HELP_URL = "https://github.com/PowerWordTree/DynamicWatchExpression"

PLUGIN_GROUPS = ("pwt.dynamic_watch_expression.plugin",)
PLUGIN_TEMPLATES = (
    "pwt.dynamic_watch_expression.plugins.{}.Plugin",
    "ddns_guard_plugin_{plugin_name}.Plugin",
    "ddns_guard_plugin_{plugin_name}.plugin.Plugin",
)

ACTION_STRATEGY_DEFAULT = None
ACTION_TIMEOUT_DEFAULT = None
ACTION_RETRIES_DEFAULT = None
ACTION_DELAY_DEFAULT = None
ACTION_PLUGIN_PATTERN = r"^[a-zA-Z0-9_]{3,15}$"

GROUP_NAME_PATTERN = r"^[a-zA-Z0-9_]{3,15}$"  # r"^(?!empty$)[a-zA-Z0-9_]{3,15}$"
GROUP_NAME_RESERVED = ("empty")
GROUP_STRATEGY_DEFAULT = "continue"
GROUP_STRATEGY_TYPE = Literal["continue", "success_stop", "failure_stop"]
GROUP_TIMEOUT_DEFAULT = 60
GROUP_RETRIES_DEFAULT = 0
GROUP_DELAY_DEFAULT = 1

WATCHER_NAME_DEFAULT = ""
WATCHER_NAME_FORMAT = "Watcher_{}"
WATCHER_NAME_PATTERN = r"^[a-zA-Z0-9@#&+._-]{3,15}$"
WATCHER_INTERVAL_DEFAULT = 120
WATCHER_TOLERANCE_DEFAULT = 0
WATCHER_EXPRESSION_DEFAULT = "empty != empty"
WATCHER_EXPRESSION_PATTERN = (
    r"^(?:[A-Za-z0-9_]{3,15}|\(|\)|&|\||-|\^|\s)+"
    r"(?:==|!=|<=|>=|<|>)"
    r"(?:[A-Za-z0-9_]{3,15}|\(|\)|&|\||-|\^|\s)+$"
)

LOG_ROOT_NAME = __title__
LOG_OUTPUT_DEFAULT = "std"
LOG_OUTPUT_OPTIONS = ("std", "stdout", "stderr")
LOG_OUTPUT_TYPE = Literal["std", "stdout", "stderr"]
LOG_OUTPUT_FORMAT_DEFAULT = "text"
LOG_OUTPUT_FORMAT_OPTIONS = ("text", "json")
LOG_OUTPUT_FORMAT_TYPE = Literal["text", "json"]
LOG_LEVEL_DEFAULT = "INFO"
LOG_LEVEL_OPTIONS = ("CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG")
LOG_LEVEL_TYPE = Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]
LOG_LEVEL_VERBOSE = "DEBUG"
LOG_FORMAT_DEFAULT = "{levelname}: {message}"
LOG_DATE_FORMAT_DEFAULT = "%Y-%m-%d %H:%M:%S"
LOG_LEVEL_FILTERS_DEFAULT = None
LOG_NAME_FILTERS_DEFAULT = None
LOG_MSG_FILTERS_DEFAULT = None
