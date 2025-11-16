import logging
import os
from typing import Dict, Any, Optional

import yaml


def load_config(config_path: str) -> Dict[str, Any]:
    logger = logging.getLogger(__name__)

    if not os.path.exists(config_path):
        logger.error(f"Configuration file not found: {config_path}")
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

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
    logger = logging.getLogger(__name__)

    if not env_name:
        env_name = os.environ.get('DJ_AGENT_ENV', 'development')

    env_config_path = f"config/environments/{env_name}.yaml"

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


def get_merged_config(config_path: str) -> Dict[str, Any]:
    return load_config(config_path)


def get_tool_config(config: Dict[str, Any], tool_name: str) -> Optional[Dict[str, Any]]:
    logger = logging.getLogger(__name__)

    tools_config = config.get('tools', [])

    for tool_config in tools_config:
        if tool_config.get('name') == tool_name:
            return tool_config.get('config', {})

    logger.warning(f"No configuration found for tool: {tool_name}")
    return None