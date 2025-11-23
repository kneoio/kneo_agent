#!/usr/bin/env python3
import asyncio
import logging
import threading

from core.config import load_config
from core.logging_config import setup_logging
from watcher.waker import Waker
import uvicorn
from rest.web_handler import app as mcp_http_app


class ApplicationManager:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.waker = None
        self.running = True
        self.http_server = None
        self.http_thread = None

    def initialize_waker(self):
        try:
            self.waker = Waker(self.config)
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize Waker: {e}")
            return False

    def shutdown(self):
        self.running = False
        if self.http_server:
            self.http_server.should_exit = True

    def start_http_server(self):
        server_cfg = self.config.get("web_server", {})
        host = server_cfg.get("host", "0.0.0.0")
        port = int(server_cfg.get("port"))
        
        logger = logging.getLogger(__name__)
        logger.info(f"Starting HTTP server on http://{host}:{port}")
        
        config = uvicorn.Config(
            mcp_http_app,
            host=host,
            port=port,
            log_level="info",
            reload=False,
            workers=1,
            loop="asyncio"
        )
        self.http_server = uvicorn.Server(config)
        self.http_thread = threading.Thread(
            target=self.http_server.run,
            daemon=True,
            kwargs={"sockets": None}
        )
        self.http_thread.start()
        
        import time
        time.sleep(1)


def run_scheduler(waker, app_manager):
    if waker and app_manager.running:
        waker.run()


async def async_main():
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
    logger.info("v.1.3.11")

    broadcaster = config.get("broadcaster", {}).get("api_base_url")
    if broadcaster:
        logger.info(f"Broadcaster API base URL: {broadcaster}")
    else:
        logger.warning("Broadcaster API base URL not found in config or config loading failed.")

    app_manager = ApplicationManager(config)

    try:
        db_cfg = config.get("database", {}) if isinstance(config, dict) else {}
        dsn = db_cfg.get("dsn")
        if not dsn:
            logger.error("Database DSN not found in config; exiting")
            return 1

        waker_success = app_manager.initialize_waker()
        if not waker_success:
            logger.error("Waker initialization failed, exiting")
            return 1

        app_manager.start_http_server()

        if app_manager.waker:
            waker_thread = threading.Thread(
                target=run_scheduler,
                args=(app_manager.waker, app_manager),
                daemon=True
            )
            logger.info("Starting scheduler thread.")
            waker_thread.start()
        else:
            logger.error("Waker could not be initialized, scheduler thread not started.")
            return 1

        logger.info("Main thread is now waiting. Press Ctrl+C to exit.")

        while app_manager.running:
            await asyncio.sleep(1)


    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Shutting down.")
        app_manager.shutdown()
    except Exception as e:
        logger.exception(f"An unexpected error occurred: {e}")
        app_manager.shutdown()
    finally:
        pass

    logger.info("Application finished.")
    return 0


def main():
    try:
        return asyncio.run(async_main())
    except Exception as e:
        logging.error(f"Failed to run async main: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)