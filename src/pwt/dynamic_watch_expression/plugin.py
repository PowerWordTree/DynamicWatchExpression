import atexit
from abc import abstractmethod
from concurrent.futures import ThreadPoolExecutor
from types import MappingProxyType
from typing import Any, Type, TypeVar, override

from pwt.dynamic_watch_expression.constants import (
    ACTION_DELAY_DEFAULT,
    ACTION_PLUGIN_FORMATS,
    ACTION_RETRIES_DEFAULT,
    ACTION_STRATEGY_DEFAULT,
    ACTION_STRATEGY_TYPE,
    ACTION_TIMEOUT_DEFAULT,
)
from pwt.utils.plugin_base import PluginBase as _PluginBase
from pwt.utils.retry import SimpleRetry
from pwt.utils.timeout import Timeout

_executor = ThreadPoolExecutor(max_workers=1)
atexit.register(_executor.shutdown, False)


class PluginBase(_PluginBase):
    """
    插件类的基类, 为具体的插件提供了基本的结构和规范.
    所有具体的插件类都应该继承自这个基类, 并实现其抽象方法.
    """

    T = TypeVar("T", bound="PluginBase")

    def __init__(self, **_: Any) -> None:
        """
        初始化插件实例.

        子类可以随意指定参数, 但调用时会以关键字参数形式传入.
        无实质内容, 子类可以不调用父类的 `__init__` 方法.
        """

        self.plugin: str
        self.timeout: float
        self.retries: int
        self.delay: float
        self.strategy: ACTION_STRATEGY_TYPE
        self.result: list[str] | None
        self.exception: Exception | None

    @override
    def execute(self, context: MappingProxyType[str, Any]) -> None:
        """
        执行插件操作, 结果或者异常保存到实例中.

        参数:
            context: 上下文实例. 可以将额外数据保存到context.extra字典实例中.
        """

        self.result = self.exception = None
        try:
            self.result = self._execute(context)
        except Exception as ex:
            self.exception = ex

    @abstractmethod
    def _execute(self, context: MappingProxyType[str, Any]) -> list[str]:
        """
        执行插件操作.

        参数:
            context: 上下文实例. 可以将额外数据保存到context.extra字典实例中.

        返回:
            执行结果是一个字符串列表.

        异常:
            Exception: 执行插件时引发的异常.
        """

    def assess_strategy(self) -> bool:
        """
        根据给定的策略评估是否继续执行.

        返回:
            根据策略评估结果,返回布尔值.
        """

        match self.strategy:  # True: 继续; False: 停止;
            case "continue":  # 成功: True; 失败: True;
                return True
            case "success_stop":  # 成功: False; 失败: True;
                return self.exception is not None
            case "failure_stop":  # 成功: True; 失败: False;
                return self.exception is None
        return False

    def __repr__(self) -> str:
        return (
            f"Plugin(name={self.plugin}, strategy={self.strategy}, "
            f"result={self.result}, exception={repr(self.exception)})"
        )

    @classmethod
    @override
    def create_plugin(
        cls: Type[T],
        plugin: str,
        timeout: float = ACTION_TIMEOUT_DEFAULT,
        retries: int = ACTION_RETRIES_DEFAULT,
        delay: float = ACTION_DELAY_DEFAULT,
        strategy: ACTION_STRATEGY_TYPE = ACTION_STRATEGY_DEFAULT,
        **kwds: Any,
    ) -> T:
        """
        查找并初始化插件实例的工厂方法.

        参数:
            plugin: 插件的名称.
            timeout: 执行插件操作的超时时间.
            retries: 执行插件操作的重试次数.
            delay: 重试之间的延迟时间.
            strategy: 继续执行插件的评估策略.
            **kwds: 插件初始化的参数.

        返回:
            初始化的插件实例.

        异常:
            ModuleNotFoundError: 如果插件模块未找到或插件类未定义.
        """

        self = super().create_plugin(plugin, ACTION_PLUGIN_FORMATS, **kwds)
        self.plugin = plugin
        self.timeout = timeout
        self.retries = retries
        self.delay = delay
        self.strategy = strategy
        self.result = None
        self.exception = None
        self.execute = Timeout(self.execute, timeout=timeout, executor=_executor)
        self.execute = SimpleRetry(self.execute, delay=delay, retries=retries)
        return self
