import sys
from loguru import logger
from config.settings import settings

logger.remove()
logger.add(sys.stderr, level=settings.LOG_LEVEL,
           format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | {message}",
           colorize=True)
logger.add("logs/advisor.log", level="DEBUG", rotation="10 MB",
           format="{time} | {level} | {message}")

from cli.commands import cli

if __name__ == "__main__":
    cli()