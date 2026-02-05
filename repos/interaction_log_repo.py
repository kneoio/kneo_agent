from datetime import datetime
from typing import Any, Dict, Optional
import json
import uuid

from util.db_manager import DBManager


class InteractionLogRepo:
    async def insert(self, brand: str, event_type: str, level: str, message: str, 
                    metadata: Optional[Dict[str, Any]] = None, 
                    correlation_id: Optional[str] = None) -> Dict[str, Any]:
        await DBManager.init()
        pool = DBManager.get_pool()
        
        if correlation_id is None:
            correlation_id = str(uuid.uuid4())
            
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO mixpla__interaction_logs 
                (timestamp, brand, correlation_id, event_type, level, message, metadata)
                VALUES (now(), $1, $2, $3, $4, $5, $6::jsonb)
                RETURNING id, timestamp, brand, correlation_id, event_type, level, message, metadata
                """,
                brand,
                correlation_id,
                event_type,
                level,
                message,
                json.dumps(metadata) if metadata else None,
            )
            return dict(row)

    async def insert_batch(self, logs: list) -> None:
        await DBManager.init()
        pool = DBManager.get_pool()
        
        values = []
        for log in logs:
            correlation_id = log.get('correlation_id') or str(uuid.uuid4())
            values.append((
                log['brand'],
                correlation_id,
                log['event_type'],
                log['level'],
                log['message'],
                json.dumps(log.get('metadata')) if log.get('metadata') else None
            ))
        
        async with pool.acquire() as conn:
            await conn.executemany(
                """
                INSERT INTO mixpla__interaction_logs 
                (brand, correlation_id, event_type, level, message, metadata)
                VALUES ($1, $2, $3, $4, $5, $6::jsonb)
                """,
                values
            )

    async def get_by_brand(self, brand: str, limit: int = 100, 
                          event_type: Optional[str] = None) -> list:
        await DBManager.init()
        pool = DBManager.get_pool()
        
        query = """
            SELECT id, timestamp, brand, correlation_id, event_type, level, message, metadata
            FROM mixpla__interaction_logs 
            WHERE brand = $1
        """
        params = [brand]
        
        if event_type:
            query += " AND event_type = $2"
            params.append(event_type)
            query += " ORDER BY timestamp DESC LIMIT $3"
            params.append(limit)
        else:
            query += " ORDER BY timestamp DESC LIMIT $2"
            params.append(limit)
        
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]

    async def get_by_correlation(self, correlation_id: str) -> list:
        await DBManager.init()
        pool = DBManager.get_pool()
        
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, timestamp, brand, correlation_id, event_type, level, message, metadata
                FROM mixpla__interaction_logs 
                WHERE correlation_id = $1
                ORDER BY timestamp
                """,
                correlation_id,
            )
            return [dict(row) for row in rows]


interaction_log_repo = InteractionLogRepo()
