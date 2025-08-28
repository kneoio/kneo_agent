import os
import platform
import tempfile
import logging


class TempDirectoryOptimizer:
    """Simple temp directory optimizer - check once at startup"""

    _optimal_temp_dir = None

    @classmethod
    def initialize(cls):
        """Initialize once at app startup"""
        if cls._optimal_temp_dir is not None:
            return cls._optimal_temp_dir

        logger = logging.getLogger(__name__)
        system = platform.system()

        if system == "Linux":
            # Check if /dev/shm (RAM) exists and is writable
            if os.path.exists("/dev/shm") and os.access("/dev/shm", os.W_OK):
                cls._optimal_temp_dir = "/dev/shm"
                logger.info("Using RAM-based temp directory: /dev/shm")
            else:
                cls._optimal_temp_dir = tempfile.gettempdir()
                logger.info(f"Using system temp directory: {cls._optimal_temp_dir}")

        elif system == "Windows":
            # Check for R: drive (common RAM disk)
            if os.path.exists("R:\\") and os.access("R:\\", os.W_OK):
                ram_temp = "R:\\temp"
                os.makedirs(ram_temp, exist_ok=True)
                cls._optimal_temp_dir = ram_temp
                logger.info("Using RAM disk temp directory: R:\\temp")
            else:
                cls._optimal_temp_dir = tempfile.gettempdir()
                logger.info(f"Using system temp directory: {cls._optimal_temp_dir}")
        else:
            cls._optimal_temp_dir = tempfile.gettempdir()
            logger.info(f"Using system temp directory: {cls._optimal_temp_dir}")

        return cls._optimal_temp_dir

    @classmethod
    def get_temp_dir(cls):
        """Get optimal temp directory"""
        if cls._optimal_temp_dir is None:
            cls.initialize()
        return cls._optimal_temp_dir


# Simple function to use in RadioDJAgent
def get_audio_temp_dir():
    return TempDirectoryOptimizer.get_temp_dir()