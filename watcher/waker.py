import asyncio
import logging
import os
import time
from queue import Queue
from typing import Dict

from api.broadcaster_client import BroadcasterAPIClient
from cnst.brand_status import BrandStatus
from cnst.llm_types import LlmType
from core.dj_runner import DJRunner
from mcp.external.internet_mcp import InternetMCP
from mcp.live_radio_stations_mcp import LiveRadioStationsMCP
from mcp.mcp_client import MCPClient
from util.llm_factory import LlmFactory
from cnst.paths import MERGED_AUDIO_DIR


class Waker:
    def __init__(self, config: Dict):
        self.config = config
        self.loop = None
        self.mcp_client = None
        self.live_stations_mcp = None
        self.brand_queue = Queue()
        self.llmFactory = LlmFactory(config)
        self.last_activity_time = time.time()

        self.target_dir = str(MERGED_AUDIO_DIR)
        os.makedirs(self.target_dir, exist_ok=True)
        logging.info(f"Created/verified target directory at: {self.target_dir}")

        self.BASE_INTERVAL = 60
        self.TIMEOUT_PER_STATION = 300
        self.MIN_INTERVAL = 30
        self.MAX_INTERVAL = 120
        self.BACKOFF_FACTOR = 1.5
        self.ACTIVITY_THRESHOLD = 240
        self.current_interval = self.BASE_INTERVAL

    async def _process_single_station(self, station):
        try:
            logging.info(f"Processing brand: {station.name}")
            internet_mcp = InternetMCP(mcp_client=self.mcp_client, config=self.config, default_engine="Perplexity")
            api_client = BroadcasterAPIClient(self.config)
            llmType = LlmType(station.llmType) if station.llmType else None
            llmClient = self.llmFactory.get_llm_client(llmType, internet_mcp)
            runner = DJRunner(self.config, station, api_client,
                           mcp_client=self.mcp_client, 
                           llm_client=llmClient, 
                           llm_type=llmType)

            await asyncio.wait_for(runner.run(), timeout=self.TIMEOUT_PER_STATION)
            return True
        except asyncio.TimeoutError:
            logging.error(f"Timeout processing brand: {station.name}")
            return False
        except Exception as e:
            logging.error(f"DJ Agent error for {station.name}: {e}")
            return False
        finally:
            if 'runner' in locals() and hasattr(runner, 'cleanup'):
                await runner.cleanup()
            if 'api_client' in locals() and hasattr(api_client, 'close'):
                await api_client.close()

    async def process_brand_queue(self):
        tasks = []
        while not self.brand_queue.empty():
            station = self.brand_queue.get()
            tasks.append(self._process_single_station(station))
            self.brand_queue.task_done()

        if not tasks:
            return False

        results = await asyncio.gather(*tasks, return_exceptions=True)
        return any(r is True for r in results)

    async def _async_run(self):
        self.mcp_client = MCPClient(self.config, skip_initialization=True)
        await self.mcp_client.connect()
        self.live_stations_mcp = LiveRadioStationsMCP(self.mcp_client)

        try:
            while True:
                had_activity = False
                try:
                    live_container = await self.live_stations_mcp.get_live_radio_stations()
                    if live_container and len(live_container) > 0:
                        for station in live_container.radioStations:
                            if station.radioStationStatus != BrandStatus.QUEUE_SATURATED.value:
                                self.brand_queue.put(station)
                        had_activity = await self.process_brand_queue()
                except Exception as e:
                    logging.error(f"Waker error: {e}")

                self._update_interval(had_activity)
                next_run_ts = time.time() + self.current_interval
                next_run_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(next_run_ts))
                logging.info(f"Waker sleeping for {self.current_interval:.0f}s. Next run at {next_run_str}")
                await asyncio.sleep(self.current_interval)
        finally:
            await self.mcp_client.disconnect()

    def _update_interval(self, had_activity: bool):
        if had_activity:
            self.current_interval = self.BASE_INTERVAL
            self.last_activity_time = time.time()
        else:
            time_since_activity = time.time() - self.last_activity_time
            if time_since_activity > self.ACTIVITY_THRESHOLD:
                self.current_interval = min(
                    self.current_interval * self.BACKOFF_FACTOR,
                    self.MAX_INTERVAL
                )
            else:
                self.current_interval = self.BASE_INTERVAL

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._async_run())
        finally:
            self.loop.close()
