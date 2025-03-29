#!/usr/bin/env python3
# main.py - Entry point for the AI DJ Agent System

import logging
import argparse
from core.agent_v1 import DJAgent
from core.config import load_config
from core.logging_config import setup_logging


def main():
    parser = argparse.ArgumentParser(description="AI DJ Agent System")
    parser.add_argument("--config", default="config.json", help="Path to configuration file")
    args = parser.parse_args()

    log_level = logging.DEBUG if args.debug else logging.INFO
    setup_logging(log_level)
    logger = logging.getLogger(__name__)
    logger.info("Starting AI DJ Agent System")

    config = load_config(args.config)
    logger.info(f"Loaded configuration from {args.config}")

    dj_agent = AIDJAgent(config)
    logger.info("DJ Agent initialized successfully")

    try:
        dj_agent.run()
    except KeyboardInterrupt:
        logger.info("Shutting down AI DJ Agent System")
    except Exception as e:
        logger.exception(f"Error running DJ Agent: {e}")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())