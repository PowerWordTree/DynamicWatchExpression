import re
from typing import Any, Iterable, Literal, Sequence


def truncate_middle(obj: Any, length: int) -> str:
    """
    字符串内部截断

    参数:
        obj: 提供字符串的对象
        length: 长度
    返回:
        返回给定长度从字符串内部截断, 并添加` ... `作为分隔符.
            string: "abcdefghijkijklmnopqrst"    length: 10
            return: "abc ... st"
    """

    if length <= 5:
        return " ... "
    text = str(obj).replace("\n", " ").strip()
    if len(text) > length:
        begin_len = end_len = (length - 5) // 2
        begin_len += (length - 5) % 2
        text = text[:begin_len] + " ... " + text[-end_len:]
    return text


def casefold_in_list(
    value: Any,
    lst: Iterable[Any],
    on_not_found: Literal["none", "original", "exception"] = "none",
) -> Any:
    """
    在一个列表中忽视大小写查找一个值，并返回匹配的值。

    参数:
        value: 要查找的值。
        lst: 要查找的列表。
        on_not_found: 如果值未找到，如何处理。

    返回:
        如果找到匹配的值，则返回该值。
            如果未找到且 on_not_found 为 "original"，则返回原始值。
            如果未找到且 on_not_found 为 "exception"，则抛出 ValueError 异常。
            如果未找到且 on_not_found 为 "none"，则返回 None。
    """
    casefold_value = str(value).casefold()
    for item in lst:
        if str(item).casefold() == casefold_value:
            return item
    if on_not_found == "original":
        return value
    elif on_not_found == "exception":
        raise ValueError(f"The value '{value}' was not found in the list.")
    return None


def split_to_list(value: str | None, sep: str = ";") -> list[str] | None:
    """
    将字符串按指定分隔符分割成列表。

    参数:
        value: 要分割的字符串。
        sep: 分隔符。

    返回:
        分割后的列表，如果输入无法分割，则返回 None。
    """
    if value is not None:
        return [s.strip() for s in value.split(sep) if s.strip()] or None
    return None


def verify_regex(value: Any, flags: int = 0) -> re.Pattern:
    """
    验证并编译一个正则表达式。

    参数:
        value: 要验证的正则表达式字符串或已编译的正则表达式对象。
        flags: 编译正则表达式时使用的标志。

    返回:
        编译后的正则表达式对象。

    异常:
        ValueError: 如果输入的正则表达式无效。
    """
    try:
        return re.compile(value, flags)
    except Exception:
        raise ValueError(f"Invalid regular expression: {value}")


def regex_match(value: str, pattern: str | re.Pattern[str], flags: int = 0) -> str:
    """
    检查字符串是否匹配指定的正则表达式。

    参数:
        value: 要检查的字符串。
        pattern: 正则表达式字符串或已编译的正则表达式对象。
        flags: 匹配时使用的标志。

    返回:
        如果匹配成功，返回输入的字符串。

    异常:
        ValueError: 如果字符串不匹配正则表达式。
    """
    if not re.search(pattern, value, flags):
        raise ValueError(f"'{value}' should match pattern '{pattern}'")
    return value


def verify_field_unique(
    values: Iterable[Any],
    key_path: Sequence[str] | str = "",
    separator: str = ".",
    ignore_empty: bool = False,
) -> Iterable[Any]:
    """
    验证一组值中的某个字段是否唯一。

    参数:
        values: 要验证的结构的集合.
        key_path: 要获取值的键路径.
        separator: 当`key_path`是字符串时, 用于分隔键路径的字符.
        ignore_empty: 是否忽略空值.

    返回:
        验证后的原数据集合对象.

    异常:
        ValueError: 如果发现重复值，则抛出此异常。
    """
    value_list = [get_nested_value(v, key_path, separator) for v in values]
    if ignore_empty:
        value_list = [v for v in value_list if v]
    value_set = set(value_list)
    if len(value_list) != len(value_set):
        raise ValueError(f"Duplicate values found in {values}")
    return values


def set_field_by_index(
    values: Iterable[Any],
    format: str,
    key_path: Sequence[str] | str,
    separator: str = ".",
    only_empty: bool = False,
) -> Iterable[Any]:
    """
    根据索引设置嵌套数据结构中的字段内容.

    参数:
        values: 要修改数据结构的集合.
        format: 要设置值的格式字符串.
        key_path: 指向要设置字段的键路径.
            如果空值或者路径不存在, 抛出异常.
        separator: 用于分隔键路径的字符.
        only_empty: 是否仅修改空字段.

    返回:
        修改后的原数据集合对象.
    """

    if isinstance(key_path, str):
        key_path = key_path.split(separator) if key_path else []
    for index, value in enumerate(values):
        value = get_nested_value(value, key_path[:-1])
        if only_empty:
            if has_value(value, key_path[-1]) and get_value(value, key_path[-1]):
                continue
        set_value(value, key_path[-1], format.format(index))
    return values


def get_nested_value(
    data: Any, key_path: Sequence[str] | str, separator: str = "."
) -> Any:
    """
    从嵌套的数据结构中获取值.

    参数:
        data: 要查询的数据结构.
        key_path: 要获取值的键路径.
        separator: 当`key_path`是字符串时, 用于分隔键路径的字符.

    返回:
        键路径对应的值. 如果`key_path`为空值, 返回原数据. 如果键路径不存在, 抛出异常.
    """
    if isinstance(key_path, str):
        key_path = key_path.split(separator) if key_path else []
    value = data
    for key in key_path:
        value = get_value(value, key)
    return value


def set_nested_value(
    data: Any, value: Any, key_path: Sequence[str] | str, separator: str = "."
) -> Any:
    """
    在嵌套的数据结构中设置一个值.

    参数:
        data: 要修改的数据结构.
        value: 要设置的值.
        key_path: 要设置值的键的路径.
            如果空值或者路径不存在, 抛出异常.
        separator: 当`key_path`是字符串时, 用于分隔键路径的字符.

    返回:
        修改后的原数据对象.
    """
    if isinstance(key_path, str):
        key_path = key_path.split(separator) if key_path else []
    data = get_nested_value(data, key_path[:-1])
    set_value(data, key_path[-1], value)
    return data


def has_value(data: Any, key: str) -> bool:
    """
    从数据结构中查找键.

    参数:
        data: 要查询的数据结构.
        key: 要获取值的键.

    返回:
        如果键不存在, 返回False, 否则返回True.
    """

    if isinstance(data, dict):
        return key in data
    else:
        return hasattr(data, key)


def get_value(data: Any, key: str) -> Any:
    """
    从数据结构中获取一个值.

    参数:
        data: 要查询的数据结构.
        key: 要获取值的键.

    返回:
        键对应的值. 如果键不存在, 抛出异常.
    """
    if isinstance(data, dict):
        return data[key]
    else:
        return getattr(data, key)


def set_value(data: Any, key: str, value: Any) -> Any:
    """
    在数据结构中设置一个值.

    参数:
        data: 要修改的数据结构.
        key: 要设置值的键.
        value: 要设置的值.

    返回:
        修改后的原数据对象.
    """
    if isinstance(data, dict):
        data[key] = value
    else:
        setattr(data, key, value)
    return data
