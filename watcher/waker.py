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
        self.base_interval = 120
        self.current_interval = self.base_interval
        self.min_interval = 30
        self.max_interval = 300
        self.backoff_factor = 1.5
        self.activity_threshold = 240  # secs
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

                api_client = BroadcasterAPIClient(self.config)
                llmTypeStr =  brand.get('agent', {}).get('llmType')
                llmType = LlmType(llmTypeStr) if llmTypeStr is not None else None
                llmClient = self.llmFactory.getLlmClient(llmType)
                runner = DJRunner(self.config, brand, api_client, mcp_client=self.mcp_client, llmClient=llmClient)

                asyncio.run(runner.run())
                processed_any = True
                logging.info(f"Completed processing brand: {station_name}")

            except Exception as e:
                logging.error(f"DJ Agent error for {station_name}: {e}")
            finally:
                if 'runner' in locals() and hasattr(runner, 'cleanup'):
                    asyncio.run(runner.cleanup())
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