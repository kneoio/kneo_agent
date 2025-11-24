import logging
import uuid
from typing import Dict, Any

from api.queue_api_client import QueueAPIClient

logger = logging.getLogger(__name__)



async def enqueue(
        brand: str,
        merging_method: str,
        sound_fragments: Dict[str, str],
        file_paths: Dict[str, str],
        priority: int = 10
) -> Dict[str, Any]:
    if not brand or not merging_method or not sound_fragments or not file_paths:
        return {"success": False, "error": "brand, merging_method, sound_fragments, file_paths are required"}

    from rest.app_setup import cfg
    client = QueueAPIClient(cfg)
    process_id = uuid.uuid4().hex

    payload: Dict[str, Any] = {
        "mergingMethod": merging_method,
        "soundFragments": sound_fragments,
        "filePaths": file_paths,
        "priority": priority,
    }

    try:
        enqueue_result = await client.enqueue_add(
            brand=brand,
            process_id=process_id,
            payload=payload
        )
        logger.info(f"Queue enqueue successful for {brand}, process_id={process_id}")
        return {
            "success": True,
            "process_id": process_id,
            "enqueue_result": enqueue_result
        }
    except Exception as e:
        logger.error(f"Queue enqueue failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


