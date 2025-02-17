import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Iterable

if TYPE_CHECKING:
    from pwt.dynamic_watch_expression.expression import Expression
    from pwt.dynamic_watch_expression.plugin import PluginBase


@dataclass
class Context:
    name: str
    logger: logging.Logger = field(repr=False)
    interval: float
    tolerance: int
    expression: "Expression"
    fetches: Iterable["PluginBase"]
    executes: Iterable["PluginBase"]
    attempts: int
    extra: dict[str, Any]
