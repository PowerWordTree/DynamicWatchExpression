import logging
import time
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
    set_field_by_index,
    verify_field_unique,
    verify_regex,
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


class Log(BaseModelEx):
    output: Annotated[
        str | constants.LOG_OUTPUT_TYPE,
        convert(
            casefold_in_list,
            lst=constants.LOG_OUTPUT_OPTIONS,
            on_not_found="exception",
        ),
    ] = constants.LOG_OUTPUT_DEFAULT
    level: Annotated[
        constants.LOG_LEVEL_TYPE,
        convert(str.upper),
    ] = constants.LOG_LEVEL_DEFAULT
    format: Annotated[
        str,
        check(lambda value: logging.StrFormatStyle(value).validate()),
    ] = constants.LOG_FORMAT_DEFAULT
    date_format: Annotated[
        str,
        check(time.strftime, time_tuple=time.localtime()),
    ] = constants.LOG_DATE_FORMAT_DEFAULT
    level_filters: Annotated[
        list[constants.LOG_LEVEL_TYPE] | None,
        convert_list(str.upper),
    ] = constants.LOG_LEVEL_FILTERS_DEFAULT
    name_filters: Annotated[
        list[str] | None,
        check_list(regex_match, pattern=constants.WATCHER_NAME_PATTERN),
    ] = constants.LOG_NAME_FILTERS_DEFAULT
    msg_filters: Annotated[
        list[str] | None,
        check_list(verify_regex),
    ] = constants.LOG_MSG_FILTERS_DEFAULT


class Action(BaseModelEx, extra="allow"):
    plugin: Annotated[str, Field(pattern=constants.ACTION_PLUGIN_PATTERN)]
    timeout: Annotated[float, Field(gt=0)] = constants.ACTION_TIMEOUT_DEFAULT
    retries: Annotated[int, Field(gt=0)] = constants.ACTION_RETRIES_DEFAULT
    delay: Annotated[float, Field(gt=0)] = constants.ACTION_DELAY_DEFAULT
    strategy: Annotated[
        constants.ACTION_STRATEGY_TYPE,
        convert(str.lower),
    ] = constants.ACTION_STRATEGY_DEFAULT


class Watcher(BaseModelEx):
    name: Annotated[
        str,
        Field(pattern=constants.WATCHER_NAME_PATTERN),
    ] = constants.WATCHER_NAME_DEFAULT
    interval: Annotated[float, Field(gt=0)] = constants.WATCHER_INTERVAL_DEFAULT
    tolerance: Annotated[int, Field(ge=0)] = constants.WATCHER_TOLERANCE_DEFAULT
    expression: Annotated[
        str,
        Field(pattern=constants.WATCHER_EXPRESSION_PATTERN),
    ] = constants.WATCHER_EXPRESSION_DEFAULT
    fetches: list[Action]
    executes: list[Action]


class Config(BaseModelEx):
    logs: list[Log] = [Log()]
    watchers: Annotated[
        list[Watcher],
        convert(
            set_field_by_index,
            format=constants.WATCHER_NAME_FORMAT,
            key_path="name",
            only_empty=True,
        ),
        check(verify_field_unique, key_path="name"),
    ]
