from pwt.dynamic_watch_expression.expression import Expression

expression = "fetch_0 & fetch_1 == empty"

try:
    comparator = Expression(expression)
except Exception as e:
    print(type(e))
    raise

print(comparator._parse_tree.pretty())

try:
    result = comparator.evaluate(
        {
            "fetch_0": [0],
            "fetch_1": [1],
            "fetch_2": [2],
        }
    )
except Exception as e:
    print(type(e))
    raise
print(result)
