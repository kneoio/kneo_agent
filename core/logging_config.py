#!/usr/bin/env python3
# core/logging_config.py - Logging configuration module

import logging
import colorlog


def setup_logging(level=logging.INFO):
    """Configure logging for the application with colored output.

    Args:
        level: The logging level to use (default: logging.INFO)
    """
    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    ))

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers = []  # Remove any existing handlers
    root_logger.addHandler(handler)

    return root_logger