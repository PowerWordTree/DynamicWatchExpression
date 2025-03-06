from dataclasses import dataclass, field
from logging import Logger
from typing import TYPE_CHECKING, Any, Mapping, Sequence

from pwt.dynamic_watch_expression.constants import (
    GROUP_CHAIN_STRATEGY_TYPE,
    GROUP_ERROR_STRATEGY_TYPE,
)

if TYPE_CHECKING:
    from pwt.dynamic_watch_expression.config import Group
    from pwt.dynamic_watch_expression.expression import Expression
    from pwt.dynamic_watch_expression.plugin import PluginBase


@dataclass
class Context:
    name: str
    logger: Logger = field(repr=False)
    interval: float
    tolerance: int
    expression: "Expression"
    fetches: Sequence["Group"]
    executes: Sequence["Group"]
    attempts: int
    extra: Mapping[str, Any]


@dataclass
class PluginGroup:
    name: str
    chain_strategy: GROUP_CHAIN_STRATEGY_TYPE
    error_strategy: GROUP_ERROR_STRATEGY_TYPE
    plugins: Sequence["PluginBase"]
