import asyncio
from typing import Dict, Any

import asyncpg

from core.config import load_config


class DBManager:
    _pools: Dict[int, asyncpg.Pool] = {}
    _locks: Dict[int, asyncio.Lock] = {}
    _config: Dict[str, Any] = {}

    @classmethod
    def load_config(cls, config_path: str = "config.yaml") -> None:
        cfg = load_config(config_path)
        cls._config = cfg.get("database", {})

    @classmethod
    async def init(cls, dsn: str = None, ssl: bool = None) -> None:
        loop = None
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            pass
        loop_id = id(loop) if loop else 0

        if loop_id in cls._pools:
            return

        if not cls._config:
            cls.load_config()
            
        dsn = dsn or cls._config.get("dsn")
        ssl = ssl if ssl is not None else cls._config.get("ssl", False)
        
        if not dsn:
            raise ValueError("Database DSN not provided in configuration")
        
        if loop_id not in cls._locks:
            cls._locks[loop_id] = asyncio.Lock()
            
        async with cls._locks[loop_id]:
            if loop_id in cls._pools:
                return
            pool = await asyncpg.create_pool(dsn, ssl="require" if ssl else None)
            cls._pools[loop_id] = pool

    @classmethod
    def get_pool(cls) -> asyncpg.Pool:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        loop_id = id(loop) if loop else 0
        pool = cls._pools.get(loop_id)
        if pool is None:
            raise RuntimeError("DBManager not initialized for this event loop. Call DBManager.init() first.")
        return pool

    @classmethod
    async def close(cls) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        loop_id = id(loop) if loop else 0
        pool = cls._pools.pop(loop_id, None)
        if pool is not None:
            await pool.close()
