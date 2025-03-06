import logging
from datetime import datetime
from functools import partial
from typing import Annotated, Any, Callable, Iterable, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    Field,
    ValidationInfo,
    ValidatorFunctionWrapHandler,
    field_validator,
)
from pydantic_core import PydanticCustomError, PydanticUndefined

from pwt.dynamic_watch_expression import constants
from pwt.dynamic_watch_expression.utils import (
    casefold_in_list,
    regex_match,
    verify_field_unique,
    verify_regex,
    verify_reserved_keywords,
)


def convert(
    func: Callable[..., Any], ignore_none: bool = True, **kwargs: Any
) -> BeforeValidator:
    partial_func = partial(func, **kwargs)

    def validator(value: Any) -> Any:
        if ignore_none and value is None:
            return value
        try:
            return partial_func(value)
        except Exception:
            return value

    return BeforeValidator(validator)


def convert_list(
    func: Callable[..., Any], ignore_none: bool = True, **kwargs: Any
) -> BeforeValidator:
    partial_func = partial(func, **kwargs)

    def validator(values: Iterable[Any]) -> Iterable[Any]:
        if ignore_none and values is None:
            return values
        try:
            return [partial_func(value) for value in values]
        except Exception:
            return values

    return BeforeValidator(validator)


def check(
    func: Callable[..., Any], ignore_none: bool = True, **kwargs: Any
) -> AfterValidator:
    partial_func = partial(func, **kwargs)

    def validator(value: Any) -> Any:
        if ignore_none and value is None:
            return value
        try:
            partial_func(value)
        except Exception as ex:
            raise PydanticCustomError("format_error", "{str_ex}", {"str_ex": str(ex)})
        return value

    return AfterValidator(validator)


def check_list(
    func: Callable[..., Any], ignore_none: bool = True, **kwargs: Any
) -> AfterValidator:
    partial_func = partial(func, **kwargs)

    def validator(values: Iterable[Any]) -> Iterable[Any]:
        if ignore_none and values is None:
            return values
        try:
            for value in values:
                partial_func(value)
        except Exception as ex:
            raise PydanticCustomError("format_error", "{str_ex}", {"str_ex": str(ex)})
        return values

    return AfterValidator(validator)


class BaseModelEx(BaseModel):
    @field_validator("*", mode="wrap")
    @classmethod
    def use_default_value(
        cls: type[Self],
        value: Any,
        validator: ValidatorFunctionWrapHandler,
        info: ValidationInfo,
        /,
    ) -> Any:
        if value in ([], {}, (), set(), "", None):
            if info and info.field_name:
                field_info = cls.model_fields.get(info.field_name)
                if field_info:
                    default = field_info.get_default(call_default_factory=True)
                    if default is not PydanticUndefined:
                        if info.config and info.config.get("validate_default"):
                            return validator(default)
                        return default
        return validator(value)


class Action(BaseModelEx, extra="allow"):
    timeout: Annotated[
        float,
        Field(gt=0),
    ] = constants.ACTION_TIMEOUT_DEFAULT
    retries: Annotated[
        int,
        Field(gt=0),
    ] = constants.ACTION_RETRIES_DEFAULT
    delay: Annotated[
        float,
        Field(gt=0),
    ] = constants.ACTION_DELAY_DEFAULT
    plugin: Annotated[
        str,
        Field(pattern=constants.ACTION_PLUGIN_PATTERN),
    ]


class Group(BaseModelEx):
    name: Annotated[
        str,
        Field(pattern=constants.GROUP_NAME_PATTERN),
        check(verify_reserved_keywords, lst=constants.GROUP_NAME_RESERVED),
    ]
    chain_strategy: Annotated[
        constants.GROUP_CHAIN_STRATEGY_TYPE,
        convert(str.lower),
    ] = constants.GROUP_CHAIN_STRATEGY_DEFAULT
    error_strategy: Annotated[
        constants.GROUP_ERROR_STRATEGY_TYPE,
        convert(str.lower),
    ] = constants.GROUP_ERROR_STRATEGY_DEFAULT
    actions: Annotated[
        list[Action],
        Field(min_length=1),
    ]


class Watcher(BaseModelEx):
    name: Annotated[
        str,
        Field(pattern=constants.WATCHER_NAME_PATTERN),
    ]
    interval: Annotated[
        float,
        Field(gt=0),
    ] = constants.WATCHER_INTERVAL_DEFAULT
    tolerance: Annotated[
        int,
        Field(ge=0),
    ] = constants.WATCHER_TOLERANCE_DEFAULT
    expression: Annotated[
        str,
        Field(pattern=constants.WATCHER_EXPRESSION_PATTERN),
    ] = constants.WATCHER_EXPRESSION_DEFAULT
    fetches: Annotated[
        list[Group],
        Field(min_length=1),
        check(verify_field_unique, key_path="name"),
    ]
    executes: Annotated[
        list[Group],
        Field(min_length=1),
        check(verify_field_unique, key_path="name"),
    ]


class Log(BaseModelEx):
    output: Annotated[
        str | constants.LOG_OUTPUT_TYPE,
        convert(
            casefold_in_list,
            lst=constants.LOG_OUTPUT_OPTIONS,
            on_not_found="exception",
        ),
    ] = constants.LOG_OUTPUT_DEFAULT
    output_format: Annotated[
        constants.LOG_OUTPUT_FORMAT_TYPE,
        convert(str.lower),
    ] = constants.LOG_OUTPUT_FORMAT_DEFAULT
    level: Annotated[
        constants.LOG_LEVEL_TYPE,
        convert(str.upper),
    ] = constants.LOG_LEVEL_DEFAULT
    text_format: Annotated[
        str,
        check(lambda value: logging.StrFormatStyle(value).validate()),
    ] = constants.LOG_TEXT_FORMAT_DEFAULT
    date_format: Annotated[
        str | None,
        check(datetime.now().strftime),
    ] = constants.LOG_DATE_FORMAT_DEFAULT
    level_filters: Annotated[
        list[constants.LOG_LEVEL_TYPE] | None,
        convert_list(str.upper),
        Field(min_length=1),
    ] = constants.LOG_LEVEL_FILTERS_DEFAULT
    name_filters: Annotated[
        list[str] | None,
        Field(min_length=1),
        check_list(regex_match, pattern=constants.WATCHER_NAME_PATTERN),
    ] = constants.LOG_NAME_FILTERS_DEFAULT
    msg_filters: Annotated[
        list[str] | None,
        Field(min_length=1),
        check_list(verify_regex),
    ] = constants.LOG_MSG_FILTERS_DEFAULT


class Config(BaseModelEx):
    logs: Annotated[
        list[Log],
        Field(min_length=1),
    ] = [Log()]
    watchers: Annotated[
        list[Watcher],
        Field(min_length=1),
        check(verify_field_unique, key_path="name"),
    ]


# TODO: verify_field_unique需要重构, 未完善异常处理
