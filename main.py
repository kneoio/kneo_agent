#!/usr/bin/env python3
import logging
import argparse
import threading
import time

from core.config import load_config
from core.logging_config import setup_logging
from watcher.waker import Waker


def run_scheduler(waker):
    waker.run()


def main():
    parser = argparse.ArgumentParser(description="AI DJ Agent System")
    parser.add_argument("--config", default="config.yaml", help="Path to configuration file")
    args = parser.parse_args()

    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting AI DJ Agent System")

    config = load_config(args.config)
    logger.info(f"Loaded configuration from {args.config}")

    waker = Waker(config)

    waker_thread = threading.Thread(
        target=run_scheduler,
        args=(waker,),
        daemon=True
    )
    waker_thread.start()

    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        logger.info("Shutting down AI DJ Agent System")

    return 0


if __name__ == "__main__":
    exit(main())