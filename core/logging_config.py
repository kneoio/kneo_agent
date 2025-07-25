import logging
import logging.handlers
import colorlog
import os


def setup_logging(console_level=logging.INFO, file_level=logging.DEBUG, log_directory="logs",
                  log_file="application.log", rotate_when='midnight', rotate_interval=1,
                  rotate_backup_count=7):
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    console_handler = colorlog.StreamHandler()
    console_formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        log_colors={
            'DEBUG': 'cyan', 'INFO': 'green', 'WARNING': 'yellow',
            'ERROR': 'red', 'CRITICAL': 'red,bg_white',
        },
        reset=True, style='%'
    )
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(console_level)
    root_logger.addHandler(console_handler)

    absolute_log_directory = os.path.abspath(log_directory)
    log_file_path = os.path.join(absolute_log_directory, log_file)

    try:
        os.makedirs(absolute_log_directory, exist_ok=True)
    except OSError as e:
        logging.error(f"Failed to create log directory {absolute_log_directory}: {e}")

    file_handler = logging.handlers.TimedRotatingFileHandler(
        log_file_path,
        when=rotate_when,
        interval=rotate_interval,
        backupCount=rotate_backup_count,
        encoding='utf-8'
    )
    file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(file_level)
    root_logger.addHandler(file_handler)

    # Setup separate loggers for prompts and AI outputs
    setup_ai_loggers(absolute_log_directory, rotate_when, rotate_interval, rotate_backup_count)

    logging.info(f"Logging setup complete. Logs directed to {log_file_path} with rotation.")
    return root_logger


def setup_ai_loggers(log_directory, rotate_when='midnight', rotate_interval=1, rotate_backup_count=7):
    """Setup shared logger for AI prompts and outputs"""

    # Combined AI logger for both prompts and outputs
    ai_logger = logging.getLogger('tools.interaction_tools.ai')
    ai_logger.setLevel(logging.INFO)
    ai_logger.propagate = False

    if not ai_logger.handlers:
        ai_file = os.path.join(log_directory, 'ai_interactions.log')
        ai_handler = logging.handlers.TimedRotatingFileHandler(
            ai_file, when=rotate_when, interval=rotate_interval,
            backupCount=rotate_backup_count, encoding='utf-8'
        )
        ai_formatter = logging.Formatter('%(asctime)s - %(message)s')
        ai_handler.setFormatter(ai_formatter)
        ai_logger.addHandler(ai_handler)