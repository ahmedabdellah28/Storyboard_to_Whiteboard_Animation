"""
Structured Logging Configuration for Studio Application & Engine.
"""
import logging
import sys

def setup_logger(name: str = "StudioApp", level: int = logging.INFO) -> logging.Logger:
    """Returns a configured standard Python logger."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(level)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        formatter = logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger

app_logger = setup_logger("StudioApp")
render_logger = setup_logger("RenderEngine")
