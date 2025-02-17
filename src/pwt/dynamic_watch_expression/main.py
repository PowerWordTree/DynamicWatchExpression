import argparse
import os
import sys
import tempfile
import traceback
from types import TracebackType
from typing import Any, Iterable

import pydantic
import tomllib
from lark import UnexpectedInput

from pwt.dynamic_watch_expression import __version__, core, log
from pwt.dynamic_watch_expression.config import Config, Log
from pwt.dynamic_watch_expression.constants import (
    HELP_URL,
    LOG_LEVEL_DEFAULT,
    LOG_LEVEL_OPTIONS,
    LOG_LEVEL_VERBOSE,
    LOG_ROOT_NAME,
)

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
        root_logger.info("Received Ctrl+C signal, Exiting...")
    else:
        fd, path = tempfile.mkstemp(prefix="traceback-", suffix=".log", text=True)
        with os.fdopen(fd, mode="w") as file:
            traceback.print_exception(exc_type, exc_value, exc_traceback, file=file)
        root_logger.critical(f"{exc_type.__name__}: {str(exc_value)}")
        root_logger.critical(f"Unexpected error. Traceback log at: {path}")


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
        root_logger.critical(f"{type(ex).__name__}: {str(ex)}")
        raise SystemExit(2)


def _get_parser() -> argparse.ArgumentParser:
    """
    创建并返回一个命令行参数解析器.

    返回:
        一个配置好的命令行参数解析器.
    """

    parser = argparse.ArgumentParser(
        epilog=f"若需获取更详细的信息, 请访问网站: {HELP_URL}",
        add_help=False,
        exit_on_error=False,
    )
    parser.add_argument(
        "config_file",
        metavar="CONFIG_FILE",
        help="配置文件, 必要参数",
        type=argparse.FileType(mode="rb"),
    )
    parser.add_argument(
        "--log-output",
        help="设置日志输出, 选项: std/stdout/stderr/filename.ext",
    )
    parser.add_argument(
        "--log-format",
        help="设置日志格式, 传递printf风格的格式化字符串",
    )
    parser.add_argument(
        "--log-level-filters",
        help="设置日志等级过滤, 可多次设置, 对日志等级匹配",
        type=str.upper,
        action="append",
        choices=LOG_LEVEL_OPTIONS,
    )
    parser.add_argument(
        "--log-name-filters",
        help="设置日志名称过滤, 可多次设置, 对监视器名称匹配",
        action="append",
    )
    parser.add_argument(
        "--log-msg-filters",
        help="设置日志内容过滤, 可多次设置, 对日志内容进行正则匹配",
        action="append",
    )
    parser_log_level = parser.add_mutually_exclusive_group()
    parser_log_level.add_argument(
        "--log-level",
        help=f"设置日志输出级别, 默认: {LOG_LEVEL_DEFAULT}",
        type=str.upper,
        choices=LOG_LEVEL_OPTIONS,
    )
    parser_log_level.add_argument(
        "--verbose",
        "-v",
        help=f"显示详细信息, 等同: --log-level={LOG_LEVEL_VERBOSE}",
        dest="log_level",
        action="store_const",
        const=LOG_LEVEL_VERBOSE,
    )
    parser.add_argument(
        "--version",
        "-V",
        help="显示版本号",
        action="version",
        version=__version__,
    )
    parser.add_argument(
        "--help",
        "-h",
        help="显示帮助",
        action="help",
    )
    return parser


def read_config_file(args: argparse.Namespace) -> dict[str, Any]:
    """
    读取并解析配置文件.

    参数:
        args: 包含命令行参数的命名空间对象.

    返回:
        解析后的配置文件内容, 以字典形式返回.
    """

    try:
        with args.config_file as file:
            return tomllib.load(file)
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as ex:
        root_logger.critical(f"{type(ex).__name__}: {str(ex)}")
        raise SystemExit(3)


def update_log_config(config: dict[str, Any], args: argparse.Namespace) -> None:
    """
    根据命令行参数更新日志配置.

    参数:
        config: 包含配置信息的字典.
        args: 包含命令行参数的命名空间对象.

    """

    log = {}
    if args.log_output is not None:
        log.update(output=args.log_output)
    if args.log_format is not None:
        log.update(format=args.log_format)
    if args.log_level is not None:
        log.update(level=args.log_level)
    if args.log_level_filters is not None:
        log.update(level_filters=args.log_level_filters)
    if args.log_name_filters is not None:
        log.update(name_filters=args.log_name_filters)
    if args.log_msg_filters is not None:
        log.update(msg_filters=args.log_msg_filters)
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
        for error in ex.errors():
            field = ".".join(str(s) for s in error.get("loc", []))
            msg = error.get("msg", "")
            root_logger.critical(f"ConfigError: {field}: {msg}")
        raise SystemExit(3)


def setup_root_logger(log_config: Iterable[Log]) -> None:
    """
    根据日志配置设置根日志记录器的处理器。

    参数:
        log_config (Iterable[Log]): 包含日志配置的可迭代对象。
    """

    # 获取处理器
    try:
        handlers = log.get_handlers(log_config)
    except OSError as ex:
        msg = f"OSError: {ex.strerror}"
        filenames = ", ".join(f"'{s}'" for s in (ex.filename, ex.filename2) if s)
        if filenames:
            msg += f": {filenames}"
        root_logger.critical(msg)
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


def run_core(config: Config) -> None:
    """
    运行核心逻辑, 启动监视器任务.

    参数:
        config: 包含配置信息的Config对象.
    """

    try:
        return core.start_watchers(config.watchers, root_logger)
    except (UnexpectedInput, ModuleNotFoundError) as ex:
        root_logger.critical(f"{type(ex).__name__}: {str(ex)}")
        raise SystemExit(3)


def main() -> int:
    # 全局异常处理器
    sys.excepthook = global_exception_handler
    # 解析命令行
    args = parse_args()
    # print("\nARGS:", args, "\n")  # DEBUG
    # 读取配置文件
    config_file = read_config_file(args)
    # print("\nConfigFile:", config_file, "\n")  # DEBUG
    # 更新日志设置
    update_log_config(config_file, args)
    # print("\nConfigFile:", config_file, "\n")  # DEBUG
    # 解析配置文件
    config = parse_config_file(config_file)
    # print("\nConfig:", config, "\n")  # DEBUG
    # 设置日志
    setup_root_logger(config.logs)
    # 启动任务
    run_core(config)
    return 0


if __name__ == "__main__":
    sys.exit(main())
