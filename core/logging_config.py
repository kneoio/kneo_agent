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
        os.makedirs(absolute_log_directory, exist_ok=True, mode=0o755)
    except OSError as e:
        logging.error(f"Failed to create log directory {absolute_log_directory}: {e}")
        raise

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

    setup_ai_loggers(absolute_log_directory, rotate_when, rotate_interval, rotate_backup_count)
    
    httpx_logger = logging.getLogger('httpx')
    httpx_logger.setLevel(logging.WARNING)

    logging.info(f"Logging setup complete. Logs directed to {log_file_path} with rotation.")
    return root_logger


def setup_ai_loggers(log_directory, rotate_when='midnight', rotate_interval=1, rotate_backup_count=7, brand=None):
    logger_name = f'tools.interaction_tools.ai{f".{brand}" if brand else ""}'
    ai_logger = logging.getLogger(logger_name)
    ai_logger.setLevel(logging.INFO)
    ai_logger.propagate = False

    if not ai_logger.handlers:
        log_filename = f'ai_interactions{f"_{brand}" if brand else ""}.log'
        ai_file = os.path.join(log_directory, log_filename)
        
        try:
            ai_handler = logging.handlers.TimedRotatingFileHandler(
                ai_file, when=rotate_when, interval=rotate_interval,
                backupCount=rotate_backup_count, encoding='utf-8'
            )
            ai_formatter = logging.Formatter('%(asctime)s - %(message)s')
            ai_handler.setFormatter(ai_formatter)
            ai_logger.addHandler(ai_handler)
        except OSError as e:
            logging.error(f"Failed to create AI log file {ai_file}: {e}")
            raise


def setup_brand_ai_logger(brand, log_directory="logs"):
    absolute_log_directory = os.path.abspath(log_directory)
    try:
        os.makedirs(absolute_log_directory, exist_ok=True, mode=0o755)
    except OSError as e:
        logging.error(f"Failed to create log directory {absolute_log_directory}: {e}")
        raise
    
    setup_ai_loggers(absolute_log_directory, brand=brand)
    return logging.getLogger(f"tools.interaction_tools.ai.{brand}")
