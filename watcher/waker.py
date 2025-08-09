import time
import requests
import logging
import asyncio
from typing import Optional, Dict, List
from queue import Queue

from api.broadcaster_client import BroadcasterAPIClient
from cnst.brand_status import BrandStatus
from cnst.llm_types import LlmType
from util.llm_factory import LlmFactory
from core.dj_runner import DJRunner


class Waker:
    def __init__(self, config: Dict, mcp_client=None):
        broadcaster_config = config['broadcaster']
        self.base_url = broadcaster_config['api_base_url']
        self.api_key = broadcaster_config['api_key']
        self.timeout = broadcaster_config['api_timeout']
        self.base_interval = 180
        self.current_interval = self.base_interval
        self.min_interval = 30
        self.max_interval = 300
        self.backoff_factor = 1.5
        self.activity_threshold = 300  # after 5m it will start to slow down
        self.config = config
        self.mcp_client = mcp_client
        self.radio_station_name = None
        self.last_activity_time = time.time()
        self.brand_queue = Queue()
        self.llmFactory = LlmFactory(config)

    def get_available_brands(self) -> Optional[List[Dict]]:
        try:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            params = {
                'status': [
                    BrandStatus.WAITING_FOR_CURATOR.value,
                    BrandStatus.ON_LINE.value,
                    BrandStatus.WARMING_UP.value,
                    BrandStatus.QUEUE_SATURATED.value
                ]
            }

            response = requests.get(
                f"{self.base_url}/ai/brands/status",
                headers=headers,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()

            data = response.json()
            if isinstance(data, list):
                for i, brand in enumerate(data):
                    station_name = brand.get('radioStationName', 'Unknown')
                    station_status = brand.get('radioStationStatus', 'Unknown')
                    print(f"Brand -{i + 1}: {station_name} - {station_status}")

            if data and isinstance(data, list) and len(data) > 0:
                self.radio_station_name = data[0].get('radioStationName')

            return data

        except requests.exceptions.RequestException as e:
            logging.error(f"API request failed: {e}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            return None

    def queue_brands(self, brands: List[Dict]):
        """Add brands to processing queue"""
        queued_count = 0
        for brand in brands:
            if brand.get("radioStationStatus") != BrandStatus.QUEUE_SATURATED:
                self.brand_queue.put(brand)
                queued_count += 1

        logging.info(f"Queued {queued_count} brands for processing")

    def process_brand_queue(self) -> bool:
        """Process all brands in queue sequentially. Returns True if any brand was processed."""
        processed_any = False

        while not self.brand_queue.empty():
            brand = self.brand_queue.get()
            station_name = brand.get("radioStationName")

            try:
                logging.info(f"Processing brand: {station_name}")

                # Direct execution without threading
                api_client = BroadcasterAPIClient(self.config)
                agent = DJRunner(self.config, brand, api_client, mcp_client=self.mcp_client)

                asyncio.run(agent.run())
                processed_any = True
                logging.info(f"Completed processing brand: {station_name}")

            except Exception as e:
                logging.error(f"DJ Agent error for {station_name}: {e}")
            finally:
                if 'agent' in locals() and hasattr(agent, 'cleanup'):
                    asyncio.run(agent.cleanup())
                if 'api_client' in locals() and hasattr(api_client, 'close'):
                    asyncio.run(api_client.close())

                self.brand_queue.task_done()

        return processed_any

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

    def cleanup_agents(self, available_brands: List[Dict]):
        available_stations = {brand.get('radioStationName') for brand in available_brands}

        with self.agent_lock:
            agents_to_remove = []
            for station_name, thread in self.active_agents.items():
                if not thread.is_alive() or station_name not in available_stations:
                    agents_to_remove.append(station_name)

            for station_name in agents_to_remove:
                del self.active_agents[station_name]
                logging.info(f"Cleaned up agent for {station_name}")

    def run_agent(self, brand_config):
        station_name = brand_config.get('radioStationName')
        talkativity = brand_config.get('talkativity', 0.5)

        use_prerecorded = random.random() > talkativity

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            if use_prerecorded:
                logging.info(f"Starting prerecorded agent for {station_name}")
                prerecorded = Prerecorded(self.audio_processor, brand_config)
                loop.run_until_complete(prerecorded.process_and_broadcast())
            else:
                logging.info(f"Starting RadioDJAgent for {station_name}")
                api_client = BroadcasterAPIClient(self.config)
                llmTypeStr = brand_config.get('llmType')
                llmType = LlmType(llmTypeStr) if llmTypeStr is not None else None
                llmClient = self.llmFactory.getLlmClient(llmType)
                agent = RadioDJAgent(self.audio_processor, brand_config, api_client, mcp_client=self.mcp_client, llmClient=llmClient)
                loop.run_until_complete(agent.process_and_broadcast())
        finally:
            loop.close()

        with self.agent_lock:
            if station_name in self.active_agents:
                del self.active_agents[station_name]
                logging.info(f"Agent for {station_name} has completed")

    def run(self) -> None:
        logging.info("Starting Waker (queued single-thread mode)")
        while True:
            logging.info("Waker tick...")
            had_activity = False

            try:
                # Get available brands and queue them
                brands = self.get_available_brands()
                if brands:
                    self.queue_brands(brands)
                    # Process all queued brands one by one
                    had_activity = self.process_brand_queue()
                else:
                    logging.info("No matching brands found")

            except Exception as e:
                logging.error(f"Waker error: {e}")

            self.update_interval(had_activity)
            logging.info(f"Sleeping for {self.current_interval} seconds")
            time.sleep(self.current_interval)