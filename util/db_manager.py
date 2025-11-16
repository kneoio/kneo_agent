import asyncio
import asyncpg
from typing import Optional, Dict, Any
from core.config import get_merged_config


class DBManager:
    _pool: Optional[asyncpg.Pool] = None
    _lock = asyncio.Lock()
    _config: Dict[str, Any] = {}

    @classmethod
    def load_config(cls, config_path: str = "config.yaml") -> None:
        cfg = get_merged_config(config_path)
        cls._config = cfg.get("database", {})

    @classmethod
    async def init(cls, dsn: str = None, ssl: bool = None) -> None:
        if cls._pool is not None:
            return
            
        if not cls._config:
            cls.load_config()
            
        dsn = dsn or cls._config.get("dsn")
        ssl = ssl if ssl is not None else cls._config.get("ssl", False)
        
        if not dsn:
            raise ValueError("Database DSN not provided in configuration")
            
        async with cls._lock:
            if cls._pool is not None:
                return
            cls._pool = await asyncpg.create_pool(dsn, ssl="require" if ssl else None)

    @classmethod
    def get_pool(cls) -> asyncpg.Pool:
        if cls._pool is None:
            raise RuntimeError("DBManager not initialized. Call DBManager.init() first.")
        return cls._pool

    @classmethod
    async def close(cls) -> None:
        if cls._pool is not None:
            await cls._pool.close()
            cls._pool = None
