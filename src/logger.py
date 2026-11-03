import logging
import sys
from src.config import settings
from logtail import LogtailHandler

token = settings.BETTER_STACK_TOKEN
host = settings.BETTER_STACK_HOST
logger = logging.getLogger(__name__)

formatter = logging.Formatter(fmt="%(asctime)s - %(levelname)s - %(message)s")
stream_handler = logging.StreamHandler(sys.stdout)

stream_handler.setFormatter(formatter)
better_stack_handler = LogtailHandler(
    source_token=token,
    host=host,
)

logger.handlers = [stream_handler, better_stack_handler]

logger.setLevel("INFO")
