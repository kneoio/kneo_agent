#!/usr/bin/env python3
import asyncio
import logging
import threading

from core.config import load_config
from core.logging_config import setup_logging
from mcp.mcp_client import MCPClient
from watcher.waker import Waker
import uvicorn
from mcp.server.mcp_manager import app as mcp_http_app


class ApplicationManager:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.mcp_client = None
        self.waker = None
        self.running = True
        self.http_server = None
        self.http_thread = None

    async def initialize_mcp_client(self):
        while self.running:
            try:
                self.mcp_client = MCPClient(self.config)
                await self.mcp_client.connect()
                self.logger.info("MCP client initialized and connected")
                return True
            except Exception as e:
                self.logger.error(f"Failed to initialize MCP client: {e}")
                self.logger.info("Retrying MCP connection in 5 seconds...")
                await asyncio.sleep(5)
        return False

    async def cleanup_mcp_client(self):
        if self.mcp_client:
            await self.mcp_client.disconnect()
            self.logger.info("MCP client disconnected")

    def initialize_waker(self):
        try:
            self.waker = Waker(self.config, mcp_client=self.mcp_client)
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize Waker: {e}")
            return False

    def shutdown(self):
        self.running = False
        if self.http_server:
            self.http_server.should_exit = True

    def start_http_server(self):
        server_cfg = self.config.get("mcp_server", {})
        host = server_cfg.get("host", "0.0.0.0")
        port = int(server_cfg.get("port", 8081))
        config = uvicorn.Config(mcp_http_app, host=host, port=port, log_level="info")
        self.http_server = uvicorn.Server(config)
        self.http_thread = threading.Thread(target=self.http_server.run, daemon=True)
        self.http_thread.start()


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
    logger.info("v.1.3.9")

    broadcaster = config.get("broadcaster", {}).get("api_base_url")
    if broadcaster:
        logger.info(f"Broadcaster API base URL: {broadcaster}")
    else:
        logger.warning("Broadcaster API base URL not found in config or config loading failed.")

    app_manager = ApplicationManager(config)

    #atexit.register(lambda: asyncio.create_task(app_manager.cleanup_mcp_client()))

    try:
        logger.info("Waiting for MCP client connection...")
        mcp_success = await app_manager.initialize_mcp_client()
        if not mcp_success:
            logger.error("Application shutting down - MCP client required but unavailable")
            return 1

        logger.info("MCP client ready for use")

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
        await app_manager.cleanup_mcp_client()

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