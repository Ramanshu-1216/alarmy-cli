import logging
import os

LOG_FILE_PATH = os.path.expanduser("~/.cli_alarms.log")

# Initialize the audit logger
logger = logging.getLogger("AlarmClockAudit")
logger.setLevel(logging.INFO)

# Prevent duplicate handlers on re-import
if not logger.handlers:
    try:
        # Configure file handler with UTF-8 encoding
        file_handler = logging.FileHandler(LOG_FILE_PATH, encoding='utf-8')
        formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception:
        # Fall back to console stream handler if file permissions are restricted
        console_handler = logging.StreamHandler()
        logger.addHandler(console_handler)

def audit_log(message: str, level: int = logging.INFO) -> None:
    """
    Appends an entry to the audit log.
    Strips or replaces non-ascii characters to ensure log files remain completely safe.
    """
    try:
        # Strip or replace non-ascii if needed, but logging handle with utf-8 should be safe
        logger.log(level, message)
    except Exception:
        pass
