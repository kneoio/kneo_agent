import logging
from typing import Optional


class QueueMCP:

    def __init__(self, mcp_client):
        self.mcp_client = mcp_client
        self.logger = logging.getLogger(__name__)

    async def add_to_queue_i_s(self, brand_name: str,
                               sound_fragment_uuid,
                               file_path: Optional[str] = None,
                               priority: Optional[int] = 20) -> bool:
        payload = {
            "brand": brand_name,
            "songIds": {
                "song1": sound_fragment_uuid
            },
            "mergingMethod": "INTRO_SONG",
            "priority": priority,
        }
        if file_path:
            payload["filePaths"] = {"audio1": file_path}

        self.logger.debug(f"Calling add_to_queue with payload: {payload}")
        result = await self.mcp_client.call_tool("add_to_queue", payload)
        self.logger.info(f"Added to queue for brand {brand_name}: {result}")
        return result

    async def add_to_queue_s_i_s(self, brand_name: str,
                                 fragment_uuid_1,
                                 fragment_uuid_2,
                                 file_path: Optional[str] = None,
                                 priority: Optional[int] = 20) -> bool:
        payload = {
            "brand": brand_name,
            "songIds": {
                "song1": fragment_uuid_1,
                "song2": fragment_uuid_2
            },
            "mergingMethod": "SONG_INTRO_SONG",
            "priority": priority,
        }
        if file_path:
            payload["filePaths"] = {"audio1": file_path}

        self.logger.debug(f"Calling add_to_queue with payload: {payload}")
        result = await self.mcp_client.call_tool("add_to_queue", payload)
        self.logger.info(f"Added to queue for brand {brand_name}: {result}")
        return result

    async def add_to_queue_i_s_i_s(self, brand_name: str,
                                   fragment_uuid_1,
                                   fragment_uuid_2,
                                   file_path_1: Optional[str] = None,
                                   file_path_2: Optional[str] = None,
                                   priority: Optional[int] = 20) -> bool:
        payload = {
            "brand": brand_name,
            "songIds": {
                "song1": fragment_uuid_1,
                "song2": fragment_uuid_2
            },
            "mergingMethod": "INTRO_SONG_INTRO_SONG",
            "priority": priority,
        }
        
        file_paths = {}
        if file_path_1:
            file_paths["audio1"] = file_path_1
        if file_path_2:
            file_paths["audio2"] = file_path_2
        if file_paths:
            payload["filePaths"] = file_paths

        self.logger.debug(f"Calling add_to_queue with payload: {payload}")
        result = await self.mcp_client.call_tool("add_to_queue", payload)
        self.logger.info(f"Added to queue for brand {brand_name}: {result}")
        return result
