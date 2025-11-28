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
from api.live_stations_api import LiveStationsAPI
from util.llm_factory import LlmFactory
from util.db_manager import DBManager
from cnst.paths import MERGED_AUDIO_DIR
from tools.radio_dj_v2 import RadioDJV2
from memory.memory_summarizer import MemorySummarizer


class Waker:
    def __init__(self, config: Dict):
        self.config = config
        self.loop = None
        self.live_stations_mcp = None
        self.internet_mcp = None
        self.api_client = None
        self.brand_queue = Queue()
        self.llmFactory = LlmFactory(config)
        self.last_activity_time = time.time()
        self.db_pool = None
        self.processed_status = (config or {}).get("waker", {}).get("processed_status")
        self.loop_counter = 0
        self.memory_manager = RadioDJV2.memory_manager

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
            llmType = LlmType(station.llmType) if station.llmType else None
            llmClient = self.llmFactory.get_llm_client(llmType, self.internet_mcp)

            if llmClient is None:
                logging.warning(f"LLM client not available for station {station.name} with llmType='{station.llmType}'")
                return False

            runner = DJRunner(
                config=self.config,
                station=station,
                api_client=self.api_client,
                llm_client=llmClient,
                llm_type=llmType,
                db_pool=self.db_pool
            )

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

    async def process_brand_queue(self):
        had_success = False
        while not self.brand_queue.empty():
            station = self.brand_queue.get()
            try:
                ok = await self._process_single_station(station)
                had_success = had_success or ok
            finally:
                self.brand_queue.task_done()
        return had_success

    async def _summarize_memories(self):
        logging.info(f"_summarize_memories called. Memory manager state: {list(self.memory_manager.memory.keys())}")
        if not self.memory_manager.memory:
            logging.info("No memories to summarize")
            return

        summarizer_llm_type = self.config.get("summarizer", {}).get("llm_type", LlmType.GOOGLE)
        llm_client = self.llmFactory.get_llm_client(LlmType(summarizer_llm_type), self.internet_mcp)
        
        if llm_client is None:
            logging.warning(f"LLM client not available for summarization with llmType='{summarizer_llm_type}'")
            return

        summarizer = MemorySummarizer(llm_client, LlmType(summarizer_llm_type))
        
        for brand, memory_entries in list(self.memory_manager.memory.items()):
            if not memory_entries:
                continue
                
            memory_snapshot = memory_entries.copy()
                
            try:
                summary_data = await summarizer.summarize_brand_memory(brand, memory_snapshot)
                if summary_data:
                    success = await summarizer.save_summary(brand, summary_data)
                    if success:
                        newest_timestamp = max(entry["t"] for entry in memory_snapshot)
                        self.memory_manager.remove_entries_before(brand, newest_timestamp)
                        logging.info(f"Summarized and saved memory for brand {brand}, removed {len(memory_snapshot)} entries")
                    else:
                        logging.error(f"Failed to save summary for brand {brand}")
                else:
                    logging.warning(f"No summary generated for brand {brand}")
            except Exception as e:
                logging.error(f"Error summarizing memory for brand {brand}: {e}")

    async def _async_run(self):
        self.internet_mcp = InternetMCP(config=self.config, default_engine="Perplexity")
        self.live_stations_mcp = LiveStationsAPI(self.config)
        self.api_client = BroadcasterAPIClient(self.config)

        # Initialize DB pool once (config only)
        db_cfg = self.config.get("database", {}) if isinstance(self.config, dict) else {}
        dsn = db_cfg.get("dsn")
        if not dsn:
            logging.error("Database DSN not found in config; cannot initialize DB pool")
            return
        ssl_required = bool(db_cfg.get("ssl", False))
        logging.info(f"Initializing DB pool for Waker (config DSN first 20): {dsn[:20]}... | SSL: {ssl_required}")
        try:
            await asyncio.wait_for(DBManager.init(dsn, ssl=ssl_required), timeout=30)
            self.db_pool = DBManager.get_pool()
            logging.info("DB pool for Waker initialized")
        except asyncio.TimeoutError:
            logging.error("DB pool initialization timed out after 30s")
            return
        except Exception as e:
            logging.error(f"DB pool initialization failed: {e}", exc_info=True)
            return
        if not self.db_pool:
            logging.error("DB pool init failed for Waker")
            return

        try:
            while True:
                had_activity = False
                self.loop_counter += 1
                
                try:
                    live_container = await self.live_stations_mcp.get_live_radio_stations(self.processed_status)
                    if live_container and len(live_container) > 0:
                        for station in live_container.radioStations:
                            if station.radioStationStatus != BrandStatus.QUEUE_SATURATED.value:
                                self.brand_queue.put(station)
                        had_activity = await self.process_brand_queue()
                except Exception as e:
                    logging.error(f"Waker error: {e}")

                if self.loop_counter % 5 == 0:
                    logging.info(f"Loop counter: {self.loop_counter}, triggering memory summarization")
                    try:
                        await self._summarize_memories()
                    except Exception as e:
                        logging.error(f"Memory summarization error: {e}")
                else:
                    logging.debug(f"Loop counter: {self.loop_counter}, skipping summarization")

                self._update_interval(had_activity)
                next_run_ts = time.time() + self.current_interval
                next_run_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(next_run_ts))
                logging.info(f"Waker sleeping for {self.current_interval:.0f}s. Next run at {next_run_str}")
                await asyncio.sleep(self.current_interval)
        finally:
            try:
                await DBManager.close()
                logging.info("Waker DB pool closed")
            except Exception as e:
                logging.warning(f"Error closing Waker DB pool: {e}")

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
