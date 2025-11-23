import asyncio
import logging
import uuid
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from api.queue_api_client import QueueAPIClient

logger = logging.getLogger(__name__)

FAILED_QUEUE_DIR = Path("failed_queue_requests")


async def enqueue(
        brand: str,
        merging_method: str,
        sound_fragments: Dict[str, str],
        file_paths: Dict[str, str],
        priority: int = 10,
        max_retries: int = 3
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

    for attempt in range(max_retries):
        try:
            enqueue_result = await client.enqueue_add(
                brand=brand,
                process_id=process_id,
                payload=payload
            )

            last_event = await client.wait_until_done(brand, process_id)

            return {
                "success": True,
                "process_id": process_id,
                "enqueue_result": enqueue_result,
                "last_event": last_event
            }
        except Exception as e:
            logger.error(f"enqueue attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                logger.info(f"Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                FAILED_QUEUE_DIR.mkdir(exist_ok=True)
                failed_request = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "brand": brand,
                    "process_id": process_id,
                    "merging_method": merging_method,
                    "sound_fragments": sound_fragments,
                    "file_paths": file_paths,
                    "priority": priority,
                    "error": str(e)
                }
                filename = FAILED_QUEUE_DIR / f"{brand}_{process_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
                filename.write_text(json.dumps(failed_request, indent=2))
                logger.error(f"All retries failed. Saved to {filename}")
                return {"success": False, "error": str(e), "saved_to": str(filename)}


async def retry_failed_queue_requests() -> Dict[str, Any]:
    if not FAILED_QUEUE_DIR.exists():
        return {"retried": 0, "success": 0, "failed": 0}
    
    failed_files = list(FAILED_QUEUE_DIR.glob("*.json"))
    if not failed_files:
        return {"retried": 0, "success": 0, "failed": 0}
    
    success_count = 0
    failed_count = 0
    
    for file_path in failed_files:
        try:
            data = json.loads(file_path.read_text())
            logger.info(f"Retrying failed queue request from {file_path.name}")
            
            result = await enqueue(
                brand=data["brand"],
                merging_method=data["merging_method"],
                sound_fragments=data["sound_fragments"],
                file_paths=data["file_paths"],
                priority=data.get("priority", 10),
                max_retries=1
            )
            
            if result.get("success"):
                file_path.unlink()
                logger.info(f"Successfully retried and removed {file_path.name}")
                success_count += 1
            else:
                logger.warning(f"Retry failed for {file_path.name}")
                failed_count += 1
        except Exception as e:
            logger.error(f"Error retrying {file_path.name}: {e}")
            failed_count += 1
    
    return {
        "retried": len(failed_files),
        "success": success_count,
        "failed": failed_count
    }
