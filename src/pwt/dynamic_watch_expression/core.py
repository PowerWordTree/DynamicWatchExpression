import sched
import time
from logging import Logger
from types import MappingProxyType
from typing import Iterable, Literal

from pwt.dynamic_watch_expression import __title__, __version__, log
from pwt.dynamic_watch_expression.config import Watcher
from pwt.dynamic_watch_expression.entitiy import Context
from pwt.dynamic_watch_expression.expression import Expression
from pwt.dynamic_watch_expression.plugin import PluginBase

# TODO: 完成输出日志,日志过多
# TODO: 处理正常关闭


def start_watchers(watchers: Iterable[Watcher], root_logger: Logger) -> None:
    """
    启动监视器

    参数:
        config: 配置实例
    异常:
        FileNotFoundError, PermissionError: 读写文件错误
        UnexpectedInput: 表达式解析错误时, 将出现以下子异常之一:
            UnexpectedCharacters, UnexpectedToken, UnexpectedEOF
        ModuleNotFoundError: 如果插件模块未找到或插件类未定义.
    """

    root_logger.info(log.MSG_STARTUP, __title__, __version__)
    root_logger.info(log.MSG_INITIALIZING, "scheduler")
    scheduler = sched.scheduler(time.time, time.sleep)
    for watcher in watchers:
        _init_watcher(watcher, scheduler, root_logger)
    root_logger.info(log.MSG_INITIALIZED, "scheduler")
    root_logger.info(log.MSG_SCHEDULER_RUN)
    scheduler.run()


def _init_watcher(
    watcher: Watcher, scheduler: sched.scheduler, root_logger: Logger
) -> None:
    """
    初始化Watcher

    参数:
        watcher: 包含监视器配置的Watcher对象.
        scheduler: 调度器对象，用于安排任务执行。
        root_logger: 根日志记录器, 用于创建特定于监视器的子日志记录器.

    异常:
        UnexpectedInput: 表达式解析错误时, 将出现以下子异常之一:
            UnexpectedCharacters, UnexpectedToken, UnexpectedEOF
        ModuleNotFoundError: 如果插件模块未找到或插件类未定义.
    """

    root_logger.info(log.MSG_WATCHER_INITIALIZING, watcher.name)
    root_logger.debug(log.MSG_RAW, "watcher config", watcher)
    try:
        context = _get_context(watcher, root_logger)
        root_logger.debug(log.MSG_RAW, "watcher context", context)
    except Exception as ex:
        root_logger.error(log.MSG_WATCHER_FAILED, watcher.name, ex)
        raise
    scheduler.enter(0, 1, _watcher_task, (scheduler, context))
    root_logger.info(
        log.MSG_TASK_INFO,
        context.name,
        context.interval,
        context.tolerance,
        context.attempts,
        context.expression,
    )
    root_logger.info(log.MSG_WATCHER_INITIALIZED, watcher.name)


def _get_context(watcher: Watcher, root_logger: Logger) -> Context:
    """
    根据Watcher配置创建并返回一个Context对象。

    参数:
        watcher: 包含监视器配置的Watcher对象。
        root_logger: 根日志记录器，用于创建特定于监视器的子日志记录器。

    返回:
        包含监视器上下文信息的Context对象。
    """

    context = object.__new__(Context)
    context.name = watcher.name
    context.logger = root_logger.getChild(watcher.name)
    context.interval = watcher.interval
    context.tolerance = watcher.tolerance
    context.expression = Expression(watcher.expression)
    context.fetches = [
        PluginBase.create_plugin(**action.model_dump()) for action in watcher.fetches
    ]
    context.executes = [
        PluginBase.create_plugin(**action.model_dump()) for action in watcher.executes
    ]
    context.attempts = 0
    context.extra = {}
    return context


def _watcher_task(scheduler: sched.scheduler, context: Context) -> None:
    """
    调度器任务函数, 用于执行监视器任务并重新调度下一次执行.

    参数:
        scheduler: 调度器对象, 用于重新调度任务.
        watcher_task: 监视器任务对象, 包含监视器的配置和执行逻辑.
    """

    """
    监视器任务函数, 用于执行监视器任务并重新调度下一次执行.


    该方法首先执行所有的fetches插件, 然后评估表达式.
    如果表达式为False, 则重置尝试次数并返回.
    如果表达式为True且尝试次数小于容忍度, 则增加尝试次数并返回.
    如果达到容忍度, 该方法执行所有的executes插件.

    参数:
        scheduler: 调度器对象, 用于重新调度任务.
        watcher_task: 监视器任务对象, 包含监视器的配置和执行逻辑.
    """

    context.logger.info(log.MSG_TASK_STARTING, context.name)
    _execute_plugins(context, "fetches")  # TODO: 执行失败时,处理逻辑有问题
    if not _evaluate_expression(context):
        context.attempts = 0
        context.logger.info(log.MSG_TASK_NOT_EXPRESSION)
    elif context.attempts < context.tolerance:
        context.attempts += 1
        context.logger.info(log.MSG_TASK_NOT_TOLERANCE)
    else:
        _execute_plugins(context, "executes")  # TODO: 未处理执行失败时,不重置attempts
        context.attempts = 0
        context.logger.info(log.MSG_TASK_SUCCESS)
    context.logger.info(log.MSG_TASK_FINISHED, context.name)
    scheduler.enter(context.interval, 1, _watcher_task, (scheduler, context))


def _execute_plugins(context: Context, target: Literal["fetches", "executes"]):
    """
    执行给定的插件列表.

    参数:
        plugins: 要执行的插件列表.
    """

    context.logger.info(log.MSG_PLUGINS_STARTING, target)
    plugin_context = MappingProxyType(vars(context))
    plugins: Iterable[PluginBase] = getattr(context, target)
    for plugin in plugins:
        context.logger.info(log.MSG_PLUGIN_EXECUTING, plugin.plugin)
        plugin.execute(plugin_context)
        context.logger.debug(log.MSG_RAW, "Plugin result", plugin)
        if not plugin.assess_strategy():
            context.logger.info(log.MSG_PLUGINS_SKIPPED)
            break
        context.logger.info(log.MSG_PLUGIN_EXECUTED, plugin.plugin)
    context.extra = plugin_context.get("extra", {})
    context.logger.info(log.MSG_PLUGINS_FINISHED, target)


def _evaluate_expression(context: Context) -> bool:
    """
    评估表达式.

    返回:
        表达式的评估结果. 如果发生异常, 返回False.
    """

    context.logger.info(log.MSG_EXPRESSION_STARTING)
    variables = [plugin.result or [] for plugin in context.fetches]
    try:
        result = context.expression.evaluate(variables)
        context.logger.debug(log.MSG_RAW, "Expression evaluate result", result)
    except Exception as ex:
        context.logger.error(log.MSG_EXPRESSION_FAILED, ex)
        return False
    context.logger.info(log.MSG_EXPRESSION_FINISHED)
    return result
