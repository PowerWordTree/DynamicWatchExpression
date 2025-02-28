import argparse
import os
import platform
import sys
import tempfile
import traceback
from types import TracebackType
from typing import Any, BinaryIO, Iterable

import pydantic
import tomllib
from lark import UnexpectedInput

from pwt.dynamic_watch_expression import (
    __title__,
    __version__,
    core,
    log,
)
from pwt.dynamic_watch_expression.config import Config, Log, Watcher
from pwt.dynamic_watch_expression.constants import (
    HELP_URL,
    LOG_LEVEL_DEFAULT,
    LOG_LEVEL_OPTIONS,
    LOG_LEVEL_VERBOSE,
    LOG_OUTPUT_OPTIONS,
    LOG_ROOT_NAME,
)
from pwt.dynamic_watch_expression.message import (
    MSG_CONFIG_FILE,
    MSG_ENTITY,
    MSG_EPILOG,
    MSG_ERROR,
    MSG_ERROR_CUSTOM,
    MSG_HELP,
    MSG_LOG_FORMAT,
    MSG_LOG_LEVEL,
    MSG_LOG_LEVEL_FILTERS,
    MSG_LOG_MSG_FILTERS,
    MSG_LOG_NAME_FILTERS,
    MSG_LOG_OUTPUT,
    MSG_SIGINT,
    MSG_STARTED,
    MSG_TRACEBACK,
    MSG_VERBOSE,
    MSG_VERSION,
)
from pwt.utils.plugin_base import PluginInitError, PluginNotFoundError

# 初始化根日志实例
root_logger = log.get_standard_logger(LOG_ROOT_NAME)


def global_exception_handler(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_traceback: TracebackType | None,
) -> None:
    """
    全局异常处理函数, 用于捕获并处理程序中的异常.

    参数:
        exc_type: 异常类型.
        exc_value: 异常实例.
        exc_traceback: 异常的回溯信息.
    """

    if exc_type is KeyboardInterrupt:
        root_logger.info(MSG_SIGINT)
    else:
        fd, path = tempfile.mkstemp(prefix="traceback-", suffix=".log", text=True)
        with os.fdopen(fd, mode="w") as file:
            traceback.print_exception(exc_type, exc_value, exc_traceback, file=file)
        root_logger.critical(MSG_TRACEBACK, extra=dict(path=path), exc_info=exc_value)


def parse_args() -> argparse.Namespace:
    """
    解析命令行参数并返回一个包含解析结果的命名空间对象.

    返回:
        包含解析后的命令行参数的命名空间对象.
    """

    try:
        parser = _get_parser()
        return parser.parse_args()
    except argparse.ArgumentError as ex:
        root_logger.critical(MSG_ERROR, extra=dict(exception=ex))
        raise SystemExit(2)


def _get_parser() -> argparse.ArgumentParser:
    """
    创建并返回一个命令行参数解析器.

    返回:
        一个配置好的命令行参数解析器.
    """

    parser = argparse.ArgumentParser(
        epilog=MSG_EPILOG.format(url=HELP_URL),
        add_help=False,
        exit_on_error=False,
    )
    core_group = parser.add_argument_group("Core Parameters")
    core_group.add_argument(
        "config",
        metavar="CONFIG",
        help=MSG_CONFIG_FILE,
        type=argparse.FileType(mode="rb"),
    )
    log_config_group = parser.add_argument_group("Log Configuration")
    log_config_group.add_argument(
        "--log-level",
        help=MSG_LOG_LEVEL.format(default=LOG_LEVEL_DEFAULT),
        dest="log_level",
        type=str.upper,
        choices=LOG_LEVEL_OPTIONS,
    )
    log_config_group.add_argument(
        "--log-output",
        help=MSG_LOG_OUTPUT.format(options=", ".join(LOG_OUTPUT_OPTIONS)),
    )
    log_config_group.add_argument(
        "--log-format",
        help=MSG_LOG_FORMAT,
    )
    log_filter_group = parser.add_argument_group("Log Filtering")
    log_filter_group.add_argument(
        "--log-level-filters",
        help=MSG_LOG_LEVEL_FILTERS,
        type=str.upper,
        action="append",
        choices=LOG_LEVEL_OPTIONS,
    )
    log_filter_group.add_argument(
        "--log-name-filters",
        help=MSG_LOG_NAME_FILTERS,
        action="append",
    )
    log_filter_group.add_argument(
        "--log-msg-filters",
        help=MSG_LOG_MSG_FILTERS,
        action="append",
    )
    general_group = parser.add_argument_group("General Options")
    general_group.add_argument(
        "--verbose",
        "-v",
        help=MSG_VERBOSE.format(level=LOG_LEVEL_VERBOSE),
        dest="log_level",
        action="store_const",
        const=LOG_LEVEL_VERBOSE,
    )
    general_group.add_argument(
        "--version",
        "-V",
        help=MSG_VERSION,
        action="version",
        version=__version__,
    )
    general_group.add_argument(
        "--help",
        "-h",
        help=MSG_HELP,
        action="help",
    )
    return parser


def read_config(file: BinaryIO) -> dict[str, Any]:
    """
    读取并解析配置.

    参数:
        args: 包含命令行参数的命名空间对象.

    返回:
        解析后的配置文件内容, 以字典形式返回.
    """

    try:
        return tomllib.load(file)
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as ex:
        root_logger.critical(MSG_ERROR, extra=dict(exception=ex))
        raise SystemExit(3)


def update_log_config(config: dict[str, Any], args: argparse.Namespace) -> None:
    """
    根据命令行参数更新日志配置.

    参数:
        config: 包含配置信息的字典.
        args: 包含命令行参数的命名空间对象.

    """

    arg_mapping = {
        "log_output": "output",
        "log_format": "format",
        "log_level": "level",
        "log_level_filters": "level_filters",
        "log_name_filters": "name_filters",
        "log_msg_filters": "msg_filters",
    }
    log = {
        config_key: getattr(args, arg_name)
        for arg_name, config_key in arg_mapping.items()
        if getattr(args, arg_name, None) is not None
    }
    if log:
        config.update(logs=[log])


def parse_config_file(config_file: dict[str, Any]) -> Config:
    """
    解析配置文件并返回一个Config对象.

    参数:
        config_file: 包含配置信息的字典.

    返回:
        一个Config对象, 包含解析后的配置信息.
    """

    try:
        return Config.model_validate(config_file)
    except pydantic.ValidationError as ex:
        errors = [
            f"{'.'.join(map(str, error['loc']))}: {error['msg']}"
            for error in ex.errors()
        ]
        msg = "\n    ".join(
            [f"{len(errors)} validation error(s) for {ex.title}:", *errors]
        )
        custom = dict(
            type=type(ex).__name__,
            message=msg,
            traceback="".join(
                traceback.format_exception(type(ex), ex, ex.__traceback__)
            ),
        )
        root_logger.critical(MSG_ERROR_CUSTOM, extra=dict(exception=custom))
        raise SystemExit(3)


def setup_root_logger(log_config: Iterable[Log]) -> None:
    """
    根据日志配置设置根日志记录器的处理器.

    参数:
        log_config (Iterable[Log]): 包含日志配置的可迭代对象.
    """

    # 获取处理器
    try:
        handlers = log.get_handlers(log_config)
    except OSError as ex:
        root_logger.critical(MSG_ERROR, extra=dict(exception=ex))
        raise SystemExit(1)
    # 清空当前处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    # 添加处理器
    for handler in handlers:
        root_logger.addHandler(handler)
    # 设置级别
    root_logger.setLevel(0)
    log.autoset_level(root_logger)


def log_startup_message(config: Config) -> None:
    """
    记录程序启动信息日志.

    参数:
        config: 配置对象.
    """

    python_version = (
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )
    python_mode = f"{'64bit' if sys.maxsize > 2**32 else '32bit'}"
    extra = dict(
        program=__title__,
        version=__version__,
        os=f"{platform.platform()} {platform.architecture()[0]}",
        python=f"{python_version} {python_mode}",
        pid=os.getpid(),
    )
    root_logger.info(MSG_STARTED, extra=extra)
    root_logger.debug(MSG_ENTITY, extra=dict(target=config))


def run_core(watchers: Iterable[Watcher]) -> None:
    """
    运行核心逻辑, 启动监视器任务.

    参数:
        watchers: 包含Watcher配置的可迭代实例.
    """

    try:
        return core.start_watchers(watchers, root_logger)
    except (UnexpectedInput, PluginNotFoundError, PluginInitError) as ex:
        root_logger.critical(MSG_ERROR, extra=dict(exception=ex))
        raise SystemExit(3)


def main() -> int:
    # 全局异常处理器
    sys.excepthook = global_exception_handler
    # 解析命令行
    args = parse_args()
    # print("\nARGS:", args, "\n")  # DEBUG
    # 读取配置文件
    with args.config as file:
        config_file = read_config(file)
    # print("\nConfigFile:", config_file, "\n")  # DEBUG
    # 更新日志设置
    update_log_config(config_file, args)
    # print("\nConfigFile:", config_file, "\n")  # DEBUG
    # 解析配置文件
    config = parse_config_file(config_file)
    # 设置日志
    setup_root_logger(config.logs)
    # 记录启动信息日志
    log_startup_message(config)
    # 启动任务
    run_core(config.watchers)
    return 0


if __name__ == "__main__":
    sys.exit(main())
