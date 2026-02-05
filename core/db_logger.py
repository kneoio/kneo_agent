import logging
import asyncio
from typing import Any, Dict, Optional
from repos.interaction_log_repo import interaction_log_repo


class DBLoggerHandler(logging.Handler):
    def __init__(self, brand: str, correlation_id: Optional[str] = None):
        super().__init__()
        self.brand = brand
        self.correlation_id = correlation_id
        self._loop = None

    def emit(self, record):
        try:
            # Get or create event loop
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            metadata = {
                'module': record.module,
                'function': record.funcName,
                'line': record.lineno,
                'thread': record.thread,
                'process': record.process,
            }
            
            # Add any extra attributes from the record
            for key, value in record.__dict__.items():
                if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 
                              'pathname', 'filename', 'module', 'exc_info', 
                              'exc_text', 'stack_info', 'lineno', 'funcName',
                              'created', 'msecs', 'relativeCreated', 'thread',
                              'threadName', 'processName', 'process', 'message']:
                    metadata[key] = value
            
            # Extract event_type from extra or use default
            event_type = getattr(record, 'event_type', 'general')
            
            # Combine all metadata without truncation
            for key, value in record.__dict__.items():
                if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 
                              'pathname', 'filename', 'module', 'exc_info', 
                              'exc_text', 'stack_info', 'lineno', 'funcName',
                              'created', 'msecs', 'relativeCreated', 'thread',
                              'threadName', 'processName', 'process', 'message']:
                    metadata[key] = value
            
            # Schedule the async operation
            if loop.is_running():
                # If loop is already running, create a task
                asyncio.create_task(
                    interaction_log_repo.insert(
                        brand=self.brand,
                        event_type=event_type,
                        level=record.levelname.lower(),
                        message=record.getMessage(),
                        metadata=metadata,
                        correlation_id=self.correlation_id
                    )
                )
            else:
                # If loop is not running, run until complete
                loop.run_until_complete(
                    interaction_log_repo.insert(
                        brand=self.brand,
                        event_type=event_type,
                        level=record.levelname.lower(),
                        message=record.getMessage(),
                        metadata=metadata,
                        correlation_id=self.correlation_id
                    )
                )
        except Exception:
            self.handleError(record)


def setup_db_logger(brand: str, correlation_id: Optional[str] = None) -> logging.Logger:
    logger = logging.getLogger(f"db_logger_{brand}")
    
    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Add database handler
    db_handler = DBLoggerHandler(brand, correlation_id)
    logger.addHandler(db_handler)
    logger.setLevel(logging.INFO)
    
    # Prevent propagation to root logger to avoid duplicate logs
    logger.propagate = False
    
    return logger
