import time
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict
from queue import Queue

from api.broadcaster_client import BroadcasterAPIClient
from cnst.brand_status import BrandStatus
from cnst.llm_types import LlmType
from mcp.external.internet_mcp import InternetMCP
from mcp.live_radio_stations_mcp import LiveRadioStationsMCP
from mcp.mcp_client import MCPClient
from models.live_container import LiveContainer
from util.llm_factory import LlmFactory
from core.dj_runner import DJRunner


class Waker:
    def __init__(self, config: Dict, mcp_client=None):
        self.base_interval = 120
        self.current_interval = self.base_interval
        self.min_interval = 30
        self.max_interval = 180
        self.backoff_factor = 1.5
        self.activity_threshold = 240
        self.config = config
        self.radio_station_name = None
        self.last_activity_time = time.time()
        self.brand_queue = Queue()
        self.llmFactory = LlmFactory(config)
        self.loop = None
        self.mcp_client = None
        self.live_stations_mcp = None

    async def get_available_brands(self) -> Optional[LiveContainer]:
        try:
            live_container = await self.live_stations_mcp.get_live_radio_stations()
            if not live_container:
                logging.warning("No live radio stations found")
                return None

            desired_statuses = [
                BrandStatus.ON_LINE.value,
                BrandStatus.WARMING_UP.value,
                BrandStatus.QUEUE_SATURATED.value,
                BrandStatus.WAITING_FOR_CURATOR.value
            ]

            filtered_stations = [
                station for station in live_container.radioStations
                if station.radioStationStatus in desired_statuses
            ]

            for i, station in enumerate(filtered_stations):
                print(f"Brand -{i + 1}: {station.name} - {station.radioStationStatus}")

            if filtered_stations:
                self.radio_station_name = filtered_stations[0].name
                filtered_container = LiveContainer(radioStations=filtered_stations)
                return filtered_container

            return None

        except Exception as e:
            logging.error(f"Error getting available brands from MCP: {e}")
            return None

    def queue_brands(self, live_container: LiveContainer):
        queued_count = 0
        for station in live_container.radioStations:
            if station.radioStationStatus == BrandStatus.QUEUE_SATURATED.value:
                logging.info(f" >>>>>> Skipping brand due to queue saturated: {station.name}")
                continue
            self.brand_queue.put(station)
            queued_count += 1

        logging.info(f"Queued {queued_count} brands for processing")

    async def _process_single_station(self, station):
        try:
            logging.info(f"Processing brand: {station.name}")
            internet_mcp = InternetMCP(self.mcp_client)
            api_client = BroadcasterAPIClient(self.config)
            llmType = LlmType(station.prompt.llmType) if station.prompt.llmType else None
            llmClient = self.llmFactory.get_llm_client(llmType, internet_mcp)
            runner = DJRunner(self.config, station, api_client, mcp_client=self.mcp_client, llm_client=llmClient, llm_type=llmType)

            await asyncio.wait_for(runner.run(), timeout=120)
            logging.info(f"Successfully processed brand: {station.name}")
            return True
        except asyncio.TimeoutError:
            logging.error(f"Timeout processing brand: {station.name} (exceeded 120s)")
            return False
        except Exception as e:
            logging.error(f"DJ Agent error for {station.name}: {e}")
            return False
        finally:
            if 'runner' in locals() and hasattr(runner, 'cleanup'):
                try:
                    await runner.cleanup()
                except Exception as e:
                    logging.error(f"Cleanup error for {station.name}: {e}")
            if 'api_client' in locals() and hasattr(api_client, 'close'):
                try:
                    await api_client.close()
                except Exception as e:
                    logging.error(f"API client close error for {station.name}: {e}")

    async def process_brand_queue(self) -> bool:
        tasks = []
        stations = []

        while not self.brand_queue.empty():
            station = self.brand_queue.get()
            stations.append(station)
            task = self._process_single_station(station)
            tasks.append(task)
            self.brand_queue.task_done()

        if not tasks:
            return False

        logging.info(f"Processing {len(tasks)} stations in parallel...")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(1 for r in results if r is True)
        logging.info(f"Processed {success_count}/{len(tasks)} stations successfully")
        
        return success_count > 0

    def update_interval(self, had_activity: bool):
        if had_activity:
            self.current_interval = self.base_interval
            self.last_activity_time = time.time()
        else:
            time_since_activity = time.time() - self.last_activity_time
            if time_since_activity > self.activity_threshold:
                self.current_interval = min(
                    self.current_interval * self.backoff_factor,
                    self.max_interval
                )
            else:
                self.current_interval = self.base_interval

    async def _async_run(self):
        logging.info("Starting Waker async loop")
        
        self.mcp_client = MCPClient(self.config, skip_initialization=True)
        await self.mcp_client.connect()
        self.live_stations_mcp = LiveRadioStationsMCP(self.mcp_client)
        logging.info("Waker MCP client connected")
        
        try:
            while True:
                logging.info("Waker tick...")
                had_activity = False

                try:
                    live_container = await self.get_available_brands()
                    if live_container and len(live_container) > 0:
                        self.queue_brands(live_container)
                        had_activity = await self.process_brand_queue()
                    else:
                        logging.info("No matching brands found")

                except Exception as e:
                    logging.error(f"Waker error: {e}")

                self.update_interval(had_activity)
                next_run_time = datetime.now() + timedelta(seconds=self.current_interval)
                logging.info(
                    f"Sleeping for {self.current_interval} seconds - Next run at: {next_run_time.strftime('%Y-%m-%d %H:%M:%S')}")
                await asyncio.sleep(self.current_interval)
        finally:
            if self.mcp_client:
                await self.mcp_client.disconnect()
                logging.info("Waker MCP client disconnected")
    
    def run(self) -> None:
        logging.info("Starting Waker (queued single-thread mode with MCP)")
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        try:
            self.loop.run_until_complete(self._async_run())
        finally:
            self.loop.close()