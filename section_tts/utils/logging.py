import logging
import sys
from typing import Optional

class SectionFormatter(logging.Formatter):
    """Custom formatter providing clean [TAG] message formatting."""
    def format(self, record: logging.LogRecord) -> str:
        tag = getattr(record, "tag", record.levelname)
        msg = record.getMessage()
        return f"[{tag}] {msg}"

def get_logger(name: str = "section_tts", level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(SectionFormatter())
        logger.addHandler(handler)
        logger.setLevel(level)
        logger.propagate = False
    return logger

class TTSLogger:
    """Helper class providing direct tag-based logging methods."""
    def __init__(self, logger: Optional[logging.Logger] = None):
        self._logger = logger or get_logger()

    def log_tag(self, tag: str, message: str, level: int = logging.INFO):
        self._logger.log(level, message, extra={"tag": tag})

    def section(self, msg: str): self.log_tag("SECTION", msg)
    def script(self, msg: str): self.log_tag("SCRIPT", msg)
    def chunker(self, msg: str): self.log_tag("CHUNKER", msg)
    def planner(self, msg: str): self.log_tag("PLANNER", msg)
    def cache(self, msg: str): self.log_tag("CACHE", msg)
    def tts(self, msg: str): self.log_tag("TTS", msg)
    def analyzer(self, msg: str): self.log_tag("ANALYZER", msg)
    def consistency(self, msg: str): self.log_tag("CONSISTENCY", msg)
    def stitch(self, msg: str): self.log_tag("STITCH", msg)
    def loudness(self, msg: str): self.log_tag("LOUDNESS", msg)
    def validator(self, msg: str): self.log_tag("VALIDATOR", msg)
    def output(self, msg: str): self.log_tag("OUTPUT", msg)
    def error(self, msg: str): self.log_tag("ERROR", msg, level=logging.ERROR)
    def warn(self, msg: str): self.log_tag("WARN", msg, level=logging.WARNING)
    def debug(self, msg: str): self.log_tag("DEBUG", msg, level=logging.DEBUG)

# Shared default instance
log = TTSLogger()
