import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Iterable, Mapping

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
    fetches: Mapping[str, Iterable["PluginBase"]]
    executes: Mapping[str, Iterable["PluginBase"]]
    attempts: int
    extra: Mapping[str, Any]
