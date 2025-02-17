import logging

from pwt.dynamic_watch_expression import log
from pwt.dynamic_watch_expression.config import Log


def show_logger(logger: logging.Logger, level: int = 0):
    print("  " * level, logger)
    print("  " * (level + 1), logger.handlers)
    for child in logger.getChildren():
        show_logger(child, level + 1)


log_configs = [
    {},
    {
        "output": "E:\\abc.log",
        "level": "DEBUG",
        "format": "{asctime} {levelname}: {message}",
    },
]
logger = log.get_logger("test", [Log.model_validate(cfg) for cfg in log_configs])

show_logger(logger)

logger.debug("debug")
logger.info("info")
logger.warning("warning")
logger.error("error")
logger.critical("critical")
