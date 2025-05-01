import time
import requests
import logging
import threading
from typing import Optional, Dict, List

from api.broadcaster_client import BroadcasterAPIClient
from core.agent import AIDJAgent


class Waker:
    def __init__(self, config: Dict):
        broadcaster_config = config['broadcaster']
        self.base_url = broadcaster_config['api_base_url']
        self.api_key = broadcaster_config['api_key']
        self.timeout = broadcaster_config['api_timeout']
        self.interval = 60
        self.config = config
        self.radio_station_name = None
        self.active_agents = {}
        self.agent_lock = threading.Lock()

    def get_available_brands(self) -> Optional[List[Dict]]:
        try:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            params = {
                'status': ['ON_LINE', 'WARMING_UP']
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

    def run_agent(self, station_name):
        logging.info(f"Starting agent thread for {station_name}")
        api_client = BroadcasterAPIClient()
        agent = AIDJAgent(self.config, station_name, api_client)
        agent.run()

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
            try:
                brands = self.get_available_brands()
                if brands:
                    for brand in brands:
                        station_name = brand.get("radioStationName")

                        with self.agent_lock:
                            if station_name not in self.active_agents:
                                logging.info(f"Creating new agent for {station_name}")
                                agent_thread = threading.Thread(
                                    target=self.run_agent,
                                    args=(station_name,),
                                    daemon=True
                                )
                                self.active_agents[station_name] = agent_thread
                                agent_thread.start()
                            else:
                                logging.info(f"Agent for {station_name} already running")
                else:
                    logging.info("No matching brands found")
            except Exception as e:
                logging.error(f"Waker error: {e}")

            with self.agent_lock:
                active_brands = list(self.active_agents.keys())
            logging.info(f"Sleeping for {self.interval} seconds. Active brands: {active_brands}")
            time.sleep(self.interval)
