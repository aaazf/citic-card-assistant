import logging

from app.core.config import get_settings


def configure_logging() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logging.getLogger(__name__).info(
        "logging configured app=%s version=%s data_dir=%s",
        settings.app_name,
        settings.app_version,
        settings.data_dir,
    )
