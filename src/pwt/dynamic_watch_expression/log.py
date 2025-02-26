import json
import logging
import logging.handlers
import re
import string
import sys
import time
import traceback
from datetime import datetime
from typing import Iterable, Literal, override

from pwt.dynamic_watch_expression.config import Log


def get_standard_logger(name: str | None) -> logging.Logger:
    """
    获取日志记录器并进行基本配置.

    参数:
        name (str | None): 日志记录器的名称.

    返回:
        logging.Logger: 配置好的日志记录器.
    """

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    handler = StandardHandler()
    formatter = EnhancedFormatter("{levelname}: {message}", style="{")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def get_handlers(logs: Iterable[Log]) -> list[logging.Handler]:
    """
    根据给定的日志配置列表创建并返回日志处理器列表.

    参数:
        logs (Iterable[Log]): 日志配置的可迭代实例.

    返回:
        list[logging.Handler]: 包含根据配置创建的日志处理器的列表.

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
        handler.setFormatter(
            EnhancedFormatter(
                log.text_format,
                log.date_format,
                style="{",
                output_format=log.output_format,
            )
        )
        if log.level_filters is not None:
            handler.addFilter(LevelFilter(*log.level_filters))
        if log.name_filters is not None:
            handler.addFilter(NameFilter(*log.name_filters, match_type="suffix"))
        if log.msg_filters is not None:
            handler.addFilter(MsgFilter(*log.msg_filters))
        handlers.append(handler)
    return handlers


# fmt: off
RESERVED_FIELDS = {
    'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename', 'module',
    'exc_info', 'exc_text', 'stack_info', 'lineno', 'funcName', 'created', 'msecs',
    'relativeCreated', 'thread', 'threadName', 'processName', 'process', 'taskName',
    'message', 'asctime', 'stacklevel'
}
# fmt: on


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


class EnhancedFormatter(logging.Formatter):
    """
    扩展的格式器
    """

    def __init__(
        self,
        textfmt: str | None = None,
        datefmt: str | None = None,
        style: Literal["%", "{", "$"] = "{",
        validate: bool = True,
        *,
        output_format: Literal["text", "json"] = "text",
    ) -> None:
        super().__init__(textfmt, datefmt, style, validate)
        self.style = style
        self.output_format = output_format

    @override
    def format(self, record: logging.LogRecord) -> str:
        record.message = self.getMessage(record)
        record.asctime = self.formatTime(record, self.datefmt)

        # 输出text日志
        if self.output_format == "text":
            return self.formatMessage(record)

        log_dict = {
            # 基础字段
            "timestamp": record.asctime,
            "level": record.levelname,
            "logger": record.name,
            "message": record.message,
            # 系统信息
            "process": {"id": record.process, "name": record.processName},
            "thread": {"id": record.thread, "name": record.threadName},
            # 代码位置
            "location": {
                "module": record.module,
                "file": record.pathname,
                "function": record.funcName,
                "line": record.lineno,
            },
        }
        # 调试信息
        if record.exc_info:
            log_dict["exception"] = {
                "type": record.exc_info[0] and record.exc_info[0].__name__,
                "message": record.exc_info[1] and str(record.exc_info[1]),
                "traceback": super().formatException(record.exc_info),
            }
        if record.stack_info:
            log_dict["stack"] = super().formatStack(record.stack_info)
        # 扩展字段
        for key, value in vars(record).items():
            if key not in RESERVED_FIELDS and not key.startswith("_"):
                log_dict[key] = value
        # extra = {
        #     key: value
        #     for key, value in vars(record).items()
        #     if key not in RESERVED_FIELDS and not key.startswith("_")
        # }
        # if extra:
        #     log_dict["extra"] = extra

        # 输出json日志
        return json.dumps(
            log_dict, ensure_ascii=False, indent=2, default=self._json_default
        )

    def getMessage(self, record: logging.LogRecord) -> str:
        match self.style:
            case "%":
                return record.getMessage()
            case "{":
                return str(record.msg).format(*record.args, **vars(record))
            case "$":
                return string.Template(str(record.msg)).substitute(vars(record))
        return record.msg

    def _json_default(self, obj):
        """处理无法序列化的对象"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, time.struct_time):
            return time.strftime("%Y-%m-%dT%H:%M:%S", obj)
        if isinstance(obj, Exception):
            return {
                "type": type(obj).__name__,
                "message": str(obj),
                "traceback": "".join(
                    traceback.format_exception(type(obj), obj, obj.__traceback__)
                ),
            }
        if hasattr(obj, "__dict__"):
            return vars(obj)
        return str(obj)


class LogRecordLite(logging.LogRecord):
    @override
    def getMessage(self) -> str:
        return str(self.msg)


class LevelFilter(logging.Filter):
    """
    日志等级过滤器
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
    """

    def __init__(
        self,
        *conditions: str,
        match_type: Literal["prefix", "suffix", "exact", "regex"] = "exact",
    ) -> None:
        """
        初始化过滤器

        参数:
            names: 允许通过的日志记录器名称列表.
            match_type: 匹配模式. prefix: 前缀; suffix: 后缀; exact:精确; regex: 正则;
        """

        self.conditions = set(conditions)
        self.match_type = match_type.lower()

        if self.match_type == "regex":
            self.re_patterns = [re.compile(n) for n in self.conditions]

    def filter(self, record: logging.LogRecord) -> bool:
        """
        用于过滤日志记录的回调函数

        参数:
            record: 要过滤的日志记录
        返回:
            如果日志记录器名称在列表中, 则返回 True, 否则返回 False
        """

        name = record.name

        if self.match_type == "prefix":
            return any(name.startswith(n) for n in self.conditions)
        elif self.match_type == "suffix":
            return any(name.endswith(n) for n in self.conditions)
        elif self.match_type == "exact":
            return name in self.conditions
        elif self.match_type == "regex":
            return any(pattern.search(name) for pattern in self.re_patterns)
        return False


class MsgFilter(logging.Filter):
    """
    日志文本过滤器
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
