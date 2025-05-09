# Shared/config_loader.py
import os
from typing import Any, Dict, List, Optional

import yaml
from dotenv import load_dotenv

from .logger_config import setup_logger

logger = setup_logger(__name__)

# Determine project root relative to this file
# Assumes config_loader.py is directly inside Shared/
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CONFIG_PATH = os.path.join(PROJECT_ROOT, "Shared", "config.yaml")
ENV_PATH = os.path.join(PROJECT_ROOT, ".env")

_config: Optional[Dict[str, Any]] = None
_env_loaded: bool = False


def load_env_vars(dotenv_path: str = ENV_PATH, override: bool = False) -> bool:
    """
    Loads environment variables from .env file.

    Args:
        dotenv_path (str): Path to the .env file.
        override (bool): Whether to override existing environment variables.

    Returns:
        bool: True if .env was found and loaded, False otherwise.
    """
    global _env_loaded
    try:
        loaded = load_dotenv(dotenv_path=dotenv_path, override=override)
        if loaded:
            logger.info(f"Environment variables loaded from {dotenv_path}")
            _env_loaded = True
            return True
        else:
            # It's okay if .env doesn't exist, might use system env vars
            logger.debug(f".env file not found at {dotenv_path} or is empty.")
            return False
    except Exception as e:
        logger.error(f"Error loading .env file from {dotenv_path}: {e}")
        return False


def load_yaml_config(config_path: str = DEFAULT_CONFIG_PATH) -> Dict[str, Any]:
    """
    Loads the YAML configuration file. Caches the result.

    Args:
        config_path (str): Path to the config.yaml file.

    Returns:
        Dict[str, Any]: The loaded configuration dictionary, or empty dict on error.
    """
    global _config
    if _config is None:
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                _config = yaml.safe_load(f)
                if _config is None:  # Handle empty file case
                    _config = {}
            logger.info(f"Configuration loaded successfully from {config_path}")
        except FileNotFoundError:
            logger.error(
                f"Configuration file not found at {config_path}. Using empty config."
            )
            _config = {}
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML configuration file {config_path}: {e}")
            _config = {}
        except Exception as e:
            logger.error(
                f"Unexpected error loading config {config_path}: {e}", exc_info=True
            )
            _config = {}
    return _config


def get_config_section(section_name: str, default: Any = None) -> Any:
    """
    Gets a specific top-level section from the loaded YAML config.

    Args:
        section_name (str): The top-level key in config.yaml.
        default (Any): The value to return if the section is not found. Defaults to None.

    Returns:
        Any: The configuration section (often a dict or list), or the default value.
    """
    config = load_yaml_config()
    return config.get(section_name, default)


# --- Specific Config Getters ---


def get_scroller_config() -> Dict[str, Any]:
    """Gets the configuration specific to the scroller."""
    return get_config_section("scroller", default={})


def get_popup_config() -> List[Dict[str, Any]]:
    """Gets the list of popup configurations."""
    # Assumes popups are stored under the 'popups' key as a list
    config = get_config_section("popups", default=[])
    if not isinstance(config, list):
        logger.warning("Popup config in yaml is not a list. Returning empty list.")
        return []
    return config


def get_path_config() -> Dict[str, Any]:
    """Gets path configurations."""
    return get_config_section("paths", default={})


# --- Environment Variable Access ---
def get_env_var(var_name: str, default: Optional[str] = None) -> Optional[str]:
    """
    Gets an environment variable, loading .env if not already loaded.

    Args:
        var_name (str): The name of the environment variable.
        default (Optional[str]): The default value if the variable is not found.

    Returns:
        Optional[str]: The value of the environment variable or the default.
    """
    global _env_loaded
    if not _env_loaded:
        load_env_vars()  # Attempt to load .env if not done yet
    return os.getenv(var_name, default)


# Example usage within other modules:
# from Shared.config_loader import get_scroller_config, get_env_var
#
# scroller_cfg = get_scroller_config()
# api_key = get_env_var("AIRTABLE_API_KEY")
# like_prob = scroller_cfg.get('like_probability', 0.5) # Use .get for safety
