from types import MappingProxyType
from typing import Any, override

from pwt.dynamic_watch_expression.plugin import PluginBase


class Plugin(PluginBase):
    def __init__(self, **kwds: Any) -> None:
        self.kwds = kwds

    @override
    def _execute(self, context: MappingProxyType[str, Any]) -> list[str]:
        format_mapping = FormatMapping(context)
        results = []
        for key, value in self.kwds.items():
            result = str(value).format_map(format_mapping)
            results.append(result)
            print(f"{key}: {result}")
        return results


class FormatMapping(dict):
    def __missing__(self, key):
        return "{" + key + "}"
