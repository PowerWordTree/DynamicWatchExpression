from typing import Any, Iterable, Mapping

from lark import Lark, Token, Transformer

_GRAMMAR = r"""
    ?start: comparison
    ?comparison: calculation "==" calculation    -> equal
               | calculation "!=" calculation    -> not_equal
               | calculation "<=" calculation    -> subset
               | calculation ">=" calculation    -> superset
               | calculation "<"  calculation    -> proper_subset
               | calculation ">"  calculation    -> proper_superset
    ?calculation: factor
                | calculation "&" factor    -> intersection
                | calculation "|" factor    -> union
                | calculation "-" factor    -> difference
                | calculation "^" factor    -> symmetric_difference
    ?factor: literal | "(" calculation ")"
    ?literal: EMPTY | VARIABLE
    EMPTY: "empty"
    VARIABLE: /[A-Za-z0-9_]{1,31}/
    %import common.WS
    %ignore WS
"""

_lark = Lark(_GRAMMAR, parser="lalr")


class _EvalTransformer(Transformer[Token, bool]):
    """
    用于评估和转换语法树的类
    """

    def __init__(self, variables: Mapping[str, Iterable[Any]]) -> None:
        super().__init__()
        self._variables = variables

    def VARIABLE(self, token: Token):
        return set(self._variables.get(token, set()))

    def EMPTY(self, _):
        return set()

    def equal(self, nodes: list[set]):  # 相等
        return nodes[0] == nodes[1]

    def not_equal(self, nodes: list[set]):  # 不相等
        return nodes[0] != nodes[1]

    def subset(self, nodes: list[set]):  # 子集
        return nodes[0] <= nodes[1]

    def superset(self, nodes: list[set]):  # 超集
        return nodes[0] >= nodes[1]

    def proper_subset(self, nodes: list[set]):  # 真子集
        return nodes[0] < nodes[1]

    def proper_superset(self, nodes: list[set]):  # 真超集
        return nodes[0] > nodes[1]

    def intersection(self, nodes: list[set]):  # 交集
        return nodes[0] & nodes[1]

    def union(self, nodes: list[set]):  # 并集
        return nodes[0] | nodes[1]

    def difference(self, nodes: list[set]):  # 差集
        return nodes[0] - nodes[1]

    def symmetric_difference(self, nodes: list[set]):  # 对称差集
        return nodes[0] ^ nodes[1]


class Expression:
    """
    一个用于比较和评估表达式的类
    """

    def __init__(self, expression: str):
        """
        初始化方法

        Args:
            expression: 要评估的表达式
        Raises:
            UnexpectedInput:
                表达式解析错误时, 将出现以下子异常之一:
                UnexpectedCharacters, UnexpectedToken, UnexpectedEOF
        """

        self.expression = expression
        self._parse_tree = _lark.parse(self.expression)

    @property
    def variables(self) -> set[str]:
        """表达式中的所有变量名称集合"""
        return {
            token.value
            for token in self._parse_tree.scan_values(
                lambda t: isinstance(t, Token) and t.type == "VARIABLE"
            )
        }

    def evaluate(self, variables: Mapping[str, Iterable[Any]]) -> bool:
        """
        使用给定的字面量评估表达式

        Args:
            variables: 一个字面量字符串对应可迭代对象的字典
                每个可迭代对象代表一个字面量的值, 默认为空集合.
        Returns:
            表达式的评估结果, `True`表示表达式为真, `False`表示表达式为假.
        """

        transformer = _EvalTransformer(variables)
        return transformer.transform(self._parse_tree)

    def __repr__(self) -> str:
        return f"Expression(expression='{self.expression}')"
