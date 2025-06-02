import logging

logger = logging.getLogger("Notifier")
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO
)
