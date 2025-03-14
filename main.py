#!/usr/bin/env python3
# main.py - Entry point for the AI DJ Agent System

import logging
import argparse
from core.agent import DJAgent
from core.config import load_config
from core.logging_config import setup_logging


def main():
    """Main entry point for the AI DJ Agent System."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="AI DJ Agent System")
    parser.add_argument("--config", default="config.yaml", help="Path to configuration file")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    setup_logging(log_level)
    logger = logging.getLogger(__name__)
    logger.info("Starting AI DJ Agent System")

    # Load configuration
    config = load_config(args.config)
    logger.info(f"Loaded configuration from {args.config}")

    # Initialize DJ Agent
    dj_agent = DJAgent(config)
    logger.info("DJ Agent initialized successfully")

    # Run the agent
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