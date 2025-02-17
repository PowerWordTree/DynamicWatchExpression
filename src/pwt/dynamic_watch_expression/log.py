import logging
import logging.handlers
import re
import sys
from typing import Iterable

from pwt.dynamic_watch_expression.config import Log

MSG_STARTUP = "%s %s - started"
MSG_INITIALIZING = "Initializing %s..."
MSG_INITIALIZED = "Initialized %s."
MSG_SCHEDULER_USED = "Used Scheduler '%s' %r"
MSG_SCHEDULER_RUN = "Starting scheduler and running tasks now..."
MSG_TASK_INFO = (
    "Scheduler task '%s' info: "
    "interval: %.3f, tolerance: %d, attempts: %d, expression: %s"
)
MSG_TASK_STARTING = "Starting watcher task '%s'..."
MSG_TASK_FINISHED = "Finished watcher task '%s'..."
MSG_TASK_NOT_EXPRESSION = "Expression not satisfied, resetting attempts."
MSG_TASK_NOT_TOLERANCE = (
    "Expression satisfied, but tolerance not reached. Incremented attempts."
)
MSG_TASK_SUCCESS = "Executed action plugins, resetting attempts."
MSG_WATCHER_INITIALIZING = "Initializing watcher '%s'..."
MSG_WATCHER_FAILED = "Initialize watcher '%s' failed: %s"
MSG_WATCHER_INITIALIZED = "Initialized watcher '%s'."
MSG_PLUGINS_STARTING = "Starting execution of '%s' plugins"
MSG_PLUGINS_FINISHED = "Finished execution of '%s' plugins"
MSG_PLUGINS_SKIPPED = "Based on the strategy assessment, skipped remaining plugins."
MSG_PLUGIN_EXECUTING = "Executing plugin '%s'"
MSG_PLUGIN_EXECUTED = "Executed plugin '%s'"
MSG_EXPRESSION_STARTING = "Starting expression evaluate..."
MSG_EXPRESSION_FINISHED = "Finished expression evaluate."
MSG_EXPRESSION_FAILED = "Expression evaluating error: %s"
MSG_RAW = "%s: %r"


def get_handlers(logs: Iterable[Log]) -> list[logging.Handler]:
    """
    根据给定的日志配置列表创建并返回日志处理器列表。

    参数:
        logs (Iterable[Log]): 日志配置的可迭代实例。

    返回:
        list[logging.Handler]: 包含根据配置创建的日志处理器的列表。

    异常:
        FileNotFoundError, PermissionError: 读写文件错误
    """

    handlers = []
    for log in logs:
        match log.output:
            case "std":
                handler = StandardHandler()
            case "stdout":
                handler = logging.StreamHandler(sys.stdout)
            case "stderr":
                handler = logging.StreamHandler(sys.stderr)
            case _ as filename:
                handler = logging.handlers.WatchedFileHandler(filename)
        handler.setLevel(log.level)
        handler.setFormatter(logging.Formatter(log.format, log.date_format, "{"))
        if log.level_filters is not None:
            handler.addFilter(LevelFilter(*log.level_filters))
        if log.name_filters is not None:
            handler.addFilter(NameFilter(*log.name_filters, is_full_name=False))
        if log.msg_filters is not None:
            handler.addFilter(MsgFilter(*log.msg_filters))
        handlers.append(handler)
    return handlers


FORMAT_DATETIME = "%Y-%m-%d %H:%M:%S"
FORMAT_DATETIME_DEFAULT = "%Y-%m-%d %H:%M:%S.uuu"
# "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
FORMAT_STANDARD = "%(levelname)s: %(message)s"
FORMAT_FILE = "%(asctime)s %(levelname)s: %(message)s"
FORMAT_DEFAULT = "%(levelname)s:%(name)s:%(message)s"


class StandardHandler(logging.Handler):
    """
    标准日志处理器, 用于将日志输出到标准输出流或标准错误流.
    """

    def __init__(self):
        super().__init__()
        self.stdout = sys.stdout
        self.stderr = sys.stderr

    def flush(self):
        with self.lock:  # type: ignore
            self.stdout.flush()
            self.stderr.flush()

    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stdout if record.levelno < logging.WARNING else self.stderr
            stream.write(msg + "\n")
            stream.flush()
        except RecursionError:
            raise
        except Exception:
            self.handleError(record)

    def __repr__(self):
        level = logging.getLevelName(self.level)
        name = "<stdout> <stderr>"
        cls = type(self).__name__
        return f"<{cls} {name} ({level})>"


class LevelFilter(logging.Filter):
    """
    日志等级过滤器

    这个类用于过滤日志记录, 只允许特定日志等级的日志通过.
    初始化方法接受一个或多个日志等级作为参数.

    属性:
        levels: 允许通过的日志等级列表
    """

    def __init__(self, *levels: int | str) -> None:
        """
        初始化过滤器

        参数:
            levels: 允许通过的日志等级列表.
        异常:
            ValueError: 无此等级时抛出
        """

        self.levels = set(
            get_level(level) if isinstance(level, str) else level for level in levels
        )

    def filter(self, record: logging.LogRecord) -> bool:
        """
        用于过滤日志记录的回调函数

        参数:
            record: 要过滤的日志记录
        返回:
            如果日志等级在列表中, 则返回 True, 否则返回 False
        """

        return record.levelno in self.levels


class NameFilter(logging.Filter):
    """
    日志记录器名称过滤器

    这个类用于过滤日志记录, 只允许特定日志记录器名称的日志通过.
    初始化方法接受一个或多个日志记录器名称作为参数.

    属性:
        names: 允许通过的日志记录器名称列表
    """

    def __init__(self, *names: str, is_full_name: bool = True) -> None:
        """
        初始化过滤器

        参数:
            names: 允许通过的日志记录器名称列表.
            is_full_name: 标明 names 是日志记录器全名称还是子名称，默认为 True 表示全名称
        """

        self.names = set(names)
        self.is_full_name = is_full_name

    def filter(self, record: logging.LogRecord) -> bool:
        """
        用于过滤日志记录的回调函数

        参数:
            record: 要过滤的日志记录
        返回:
            如果日志记录器名称在列表中, 则返回 True, 否则返回 False
        """

        name = record.name if self.is_full_name else record.name.split(".")[-1]
        return name in self.names


class MsgFilter(logging.Filter):
    """
    日志文本过滤器

    这个类用于过滤日志记录, 只允许匹配正则表达式的日志通过.
    初始化方法接受一个或多个正则表达式作为参数.

    属性:
        regexps: 允许通过的正则表达式列表
    """

    def __init__(self, *regexps: str) -> None:
        """
        初始化过滤器

        参数:
            regexps: 允许通过的正则表达式列表.
        """

        self.patterns = [re.compile(s) for s in regexps]

    def filter(self, record: logging.LogRecord) -> bool:
        """
        用于过滤日志记录的回调函数

        参数:
            record: 要过滤的日志记录
        返回:
            如果匹配列表中的任意正则表达式, 则返回 True, 否则返回 False
        """

        return any(re.search(pattern, record.msg) for pattern in self.patterns)


def level_range(
    first: int = 0, last: int = 100, levels: Iterable[int] | None = None
) -> set[int]:
    """
    根据给定范围生成Level集合

    参数:
      first: 起始Level数值, 闭区间.
      last: 结束Level者数值, 闭区间.
      levels: 数值Level列表, 默认全部级别.
    返回:
      区间内的Level集合.
    """

    levels = levels or logging.getLevelNamesMapping().values()
    return {i for i in levels if i != 0 and first <= i and i <= last}


def autoset_level(
    logger: logging.Logger, default: int = logging.DEBUG, force: bool = False
) -> None:
    """
    自动设置日志级别
    根据Handler和子Logger自动设置全部级别

    参数:
        logger: 被设置的Logger实例
        default: 无法确定级别时的默认值
        force: 是否强制设置日志级别
    """

    levels = set()
    for children in logger.getChildren():
        autoset_level(children)
        levels.add(children.level)
    for handler in logger.handlers:
        filter_levels = set()
        for filter in handler.filters:
            if isinstance(filter, LevelFilter):
                filter_levels.update(filter.levels)
        filter_levels.discard(0)
        if force or not handler.level:
            handler.setLevel(min(filter_levels, default=default))
        levels.add(handler.level)
    levels.discard(0)
    if force or not logger.level:
        logger.setLevel(min(levels, default=default))


def get_level(name: str) -> int:
    """
    获取数值形式的等级

    参数:
        name: 字符串形式的等级
    返回:
        数值形式的等级
    异常:
        ValueError: 无此等级时抛出
    """

    mapping = logging.getLevelNamesMapping()
    if name not in mapping:
        raise ValueError(f"Unknown level: {name}")
    return mapping[name]


def get_standard_logger(name: str | None) -> logging.Logger:
    """
    获取日志记录器并进行基本配置。

    参数:
        name (str | None): 日志记录器的名称。

    返回:
        logging.Logger: 配置好的日志记录器。
    """

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    handler = StandardHandler()
    formatter = logging.Formatter("{levelname}: {message}", style="{")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger
