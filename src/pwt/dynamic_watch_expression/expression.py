from typing import Any, Iterable, Sequence

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
    ?literal: variable | empty
    # variable: /fetch_[0-9]+/
    variable: "fetch_" INT
    empty: "empty"
    %import common.INT
    %import common.WS
    %ignore WS
"""

_lark = Lark(_GRAMMAR, parser="lalr")


class _EvalTransformer(Transformer[Token, bool]):
    """
    用于评估和转换语法树的类
    """

    def __init__(self, variables: Sequence[Iterable[Any]]) -> None:
        super().__init__()
        self._variables = variables

    def variable(self, args):
        if isinstance(args[0], Token):
            return set(self._variables[int(args[0])])
        return args[0]

    def empty(self, _):
        return set()

    def equal(self, args):  # 相等
        return args[0] == args[1]

    def not_equal(self, args):  # 不相等
        return args[0] != args[1]

    def subset(self, args):  # 子集
        return args[0] <= args[1]

    def superset(self, args):  # 超集
        return args[0] >= args[1]

    def proper_subset(self, args):  # 真子集
        return args[0] < args[1]

    def proper_superset(self, args):  # 真超集
        return args[0] > args[1]

    def intersection(self, args):  # 交集
        return args[0] & args[1]

    def union(self, args):  # 并集
        return args[0] | args[1]

    def difference(self, args):  # 差集
        return args[0] - args[1]

    def symmetric_difference(self, args):  # 对称差集
        return args[0] ^ args[1]


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

    def evaluate(self, variables: Sequence[Iterable[Any]]) -> bool:
        """
        使用给定的字面量评估表达式

        Args:
            variables: 一个包含可迭代对象的序列, 每个可迭代对象代表一个字面量的值.
        Returns:
            表达式的评估结果, `True`表示表达式为真, `False`表示表达式为假.
        Raises:
            VisitError: 如果评估过程中发生错误.  # TODO: 需要重新检查异常抛出类型
        """

        transformer = _EvalTransformer(variables)
        return transformer.transform(self._parse_tree)

    def __repr__(self) -> str:
        return f"Expression(expression='{self.expression}')"
