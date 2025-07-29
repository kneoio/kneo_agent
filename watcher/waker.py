import time
import requests
import logging
import threading
import asyncio
from typing import Optional, Dict, List

from api.broadcaster_client import BroadcasterAPIClient
from agent.agent import AIDJAgent
from cnst.brand_status import BrandStatus


class Waker:
    def __init__(self, config: Dict, mcp_client=None):
        broadcaster_config = config['broadcaster']
        self.base_url = broadcaster_config['api_base_url']
        self.api_key = broadcaster_config['api_key']
        self.timeout = broadcaster_config['api_timeout']
        self.base_interval = 90
        self.current_interval = self.base_interval
        self.min_interval = 30
        self.max_interval = 300
        self.backoff_factor = 1.5
        self.activity_threshold = 300  # after 5m it will start to slow down
        self.config = config
        self.mcp_client = mcp_client
        self.radio_station_name = None
        self.active_agents = {}
        self.agent_lock = threading.Lock()
        self.last_activity_time = time.time()

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
                    # BrandStatus.IDLE.value
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
            if data and isinstance(data, list) and len(data) > 0:
                self.radio_station_name = data[0].get('radioStationName')

            return data

        except requests.exceptions.RequestException as e:
            logging.error(f"API request failed: {e}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            return None

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
        logging.info(f"Starting agent thread for {station_name}")

        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            api_client = BroadcasterAPIClient(self.config)
            agent = AIDJAgent(self.config, brand_config, "en", api_client, mcp_client=self.mcp_client)
            loop.run_until_complete(agent.run())
        finally:
            loop.close()

        with self.agent_lock:
            if station_name in self.active_agents:
                del self.active_agents[station_name]
                logging.info(f"Agent for {station_name} has completed")

    def run(self) -> None:
        logging.info("Starting Waker")
        while True:
            with self.agent_lock:
                active_brands = list(self.active_agents.keys())
            logging.info(f"Waker tick ... Currently active brands: {active_brands}")

            had_activity = False

            try:
                brands = self.get_available_brands()
                if brands:
                    # Clean up dead/orphaned agents
                    self.cleanup_agents(brands)

                    for brand in brands:
                        station_name = brand.get("radioStationName")

                        with self.agent_lock:
                            if station_name not in self.active_agents:
                                logging.info(f"Creating new agent for {station_name}")
                                agent_thread = threading.Thread(
                                    target=self.run_agent,
                                    args=(brand,),
                                    daemon=True
                                )
                                self.active_agents[station_name] = agent_thread
                                agent_thread.start()
                                had_activity = True
                            else:
                                logging.info(f"Agent for {station_name} already running")
                else:
                    logging.info("No matching brands found")
                    # Clean if no brands are available
                    self.cleanup_agents([])
            except Exception as e:
                logging.error(f"Waker error: {e}")

            self.update_interval(had_activity)

            with self.agent_lock:
                active_brands = list(self.active_agents.keys())
            logging.info(f"Sleeping for {self.current_interval} seconds. Active brands: {active_brands}")
            time.sleep(self.current_interval)