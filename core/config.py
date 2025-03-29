#!/usr/bin/env python3
# core/config.py - Configuration handling for the AI DJ Agent

import os
import logging
import yaml
from typing import Dict, Any, Optional


def load_config(config_path: str) -> Dict[str, Any]:
    logger = logging.getLogger(__name__)

    # Check if file exists
    if not os.path.exists(config_path):
        logger.error(f"Configuration file not found: {config_path}")
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    # Load configuration
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        logger.info(f"Loaded configuration from {config_path}")
        return config
    except yaml.YAMLError as e:
        logger.error(f"Error loading configuration from {config_path}: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error loading configuration: {e}")
        raise


def get_env_config(env_name: str = None) -> Dict[str, Any]:
    """
    Load environment-specific configuration.

    Args:
        env_name: Name of the environment profile

    Returns:
        Dictionary containing environment-specific configuration
    """
    logger = logging.getLogger(__name__)

    if not env_name:
        # Get environment from environment variable, default to 'development'
        env_name = os.environ.get('DJ_AGENT_ENV', 'development')

    env_config_path = f"config/environments/{env_name}.yaml"

    # Check if environment-specific configuration exists
    if os.path.exists(env_config_path):
        try:
            with open(env_config_path, 'r') as f:
                env_config = yaml.safe_load(f)

            logger.info(f"Loaded environment configuration for {env_name}")
            return env_config
        except Exception as e:
            logger.warning(f"Error loading environment configuration for {env_name}: {e}")
            return {}
    else:
        logger.warning(f"No environment configuration found for {env_name}")
        return {}


def get_merged_config(config_path: str, env_name: str = None) -> Dict[str, Any]:
    """
    Load and merge base configuration with environment-specific configuration.

    Args:
        config_path: Path to the base configuration file
        env_name: Name of the environment profile

    Returns:
        Dictionary containing merged configuration
    """
    base_config = load_config(config_path)
    env_config = get_env_config(env_name)

    # Merge configurations (env config takes precedence)
    merged_config = deep_merge(base_config, env_config)

    return merged_config


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries, with override taking precedence.

    Args:
        base: Base dictionary
        override: Dictionary with override values

    Returns:
        Merged dictionary
    """
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value

    return result


def get_tool_config(config: Dict[str, Any], tool_name: str) -> Optional[Dict[str, Any]]:
    """
    Get configuration for a specific tool.

    Args:
        config: Complete configuration dictionary
        tool_name: Name of the tool

    Returns:
        Tool-specific configuration or None if not found
    """
    logger = logging.getLogger(__name__)

    tools_config = config.get('tools', [])

    for tool_config in tools_config:
        if tool_config.get('name') == tool_name:
            return tool_config.get('config', {})

    logger.warning(f"No configuration found for tool: {tool_name}")
    return None