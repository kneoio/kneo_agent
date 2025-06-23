#!/usr/bin/env python3
import logging
import threading
import time

from core.config import load_config
from core.logging_config import setup_logging
from watcher.waker import Waker


def run_scheduler(waker):
    if waker:
        waker.run()


def main():
    config_file_path = "config.yaml"
    config = load_config(config_file_path)

    log_directory_from_config = config.get("logging", {}).get("directory", "default_logs")

    setup_logging(
        console_level=logging.INFO,
        file_level=logging.DEBUG,
        log_directory=log_directory_from_config
    )

    logger = logging.getLogger(__name__)
    logger.info("Application starting...")
    logger.info("v.1.95")

    broadcaster = config.get("broadcaster", {}).get("api_base_url")
    if broadcaster:
        logger.info(f"Broadcaster API base URL: {broadcaster}")
    else:
        logger.warning("Broadcaster API base URL not found in config or config loading failed.")

    waker = Waker(config)

    if waker:
        waker_thread = threading.Thread(
            target=run_scheduler,
            args=(waker,),
            daemon=True
        )
        logger.info("Starting scheduler thread.")
        waker_thread.start()
    else:
        logger.error("Waker could not be initialized, scheduler thread not started.")


    logger.info("Main thread is now waiting. Press Ctrl+C to exit.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Shutting down.")
    except Exception as e:
        logger.exception(f"An unexpected error occurred: {e}")

    logger.info("Application finished.")

    return 0

if __name__ == "__main__":
    main()