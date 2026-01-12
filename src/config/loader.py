"""
Configuration loader for competitor and crawl settings
"""
import yaml
import os
from typing import Dict, List, Any
from pathlib import Path


class ConfigurationError(Exception):
    """Raised when configuration is invalid"""
    pass


def load_competitor_config(config_path: str = None) -> Dict[str, Any]:
    """
    Load competitor configuration from YAML file
    
    Args:
        config_path: Path to competitors.yaml file. If None, uses default location.
    
    Returns:
        Dictionary containing competitor configuration
    
    Raises:
        ConfigurationError: If configuration is invalid
    """
    if config_path is None:
        # Default to config/competitors.yaml in project root
        project_root = Path(__file__).parent.parent.parent
        config_path = project_root / 'config' / 'competitors.yaml'
    
    if not os.path.exists(config_path):
        raise ConfigurationError(f"Configuration file not found: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    if not config:
        raise ConfigurationError("Configuration file is empty")
    
    # Validate configuration structure
    validate_competitor_config(config)
    
    return config


def validate_competitor_config(config: Dict[str, Any]):
    """
    Validate competitor configuration structure
    
    Args:
        config: Configuration dictionary
    
    Raises:
        ConfigurationError: If configuration is invalid
    """
    if 'competitors' not in config:
        raise ConfigurationError("Configuration must contain 'competitors' key")
    
    if not isinstance(config['competitors'], list):
        raise ConfigurationError("'competitors' must be a list")
    
    if len(config['competitors']) == 0:
        raise ConfigurationError("At least one competitor must be configured")
    
    valid_asset_types = {
        'pricing', 'features', 'changelog', 'sitemap',
        'news', 'blog', 'compliance', 'twitter'
    }
    
    valid_frequencies = {'daily', 'weekly'}
    valid_priorities = {'high', 'medium', 'low'}
    
    for competitor in config['competitors']:
        # Validate competitor structure
        if 'name' not in competitor:
            raise ConfigurationError("Competitor must have 'name' field")
        if 'base_url' not in competitor:
            raise ConfigurationError(f"Competitor '{competitor['name']}' must have 'base_url' field")
        if 'assets' not in competitor:
            raise ConfigurationError(f"Competitor '{competitor['name']}' must have 'assets' field")
        
        if not isinstance(competitor['assets'], list):
            raise ConfigurationError(f"Competitor '{competitor['name']}' assets must be a list")
        
        # Validate assets
        for asset in competitor['assets']:
            if 'type' not in asset:
                raise ConfigurationError(f"Asset in '{competitor['name']}' must have 'type' field")
            if asset['type'] not in valid_asset_types:
                raise ConfigurationError(
                    f"Invalid asset type '{asset['type']}' in '{competitor['name']}'. "
                    f"Valid types: {', '.join(valid_asset_types)}"
                )
            
            if 'url' not in asset:
                raise ConfigurationError(f"Asset in '{competitor['name']}' must have 'url' field")
            
            if 'crawl_frequency' not in asset:
                raise ConfigurationError(f"Asset in '{competitor['name']}' must have 'crawl_frequency' field")
            if asset['crawl_frequency'] not in valid_frequencies:
                raise ConfigurationError(
                    f"Invalid crawl_frequency '{asset['crawl_frequency']}' in '{competitor['name']}'. "
                    f"Valid frequencies: {', '.join(valid_frequencies)}"
                )
            
            if 'priority_threshold' in asset:
                if asset['priority_threshold'] not in valid_priorities:
                    raise ConfigurationError(
                        f"Invalid priority_threshold '{asset['priority_threshold']}' in '{competitor['name']}'. "
                        f"Valid priorities: {', '.join(valid_priorities)}"
                    )


def get_competitors(config: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """
    Get list of competitors from configuration
    
    Args:
        config: Configuration dictionary. If None, loads from default location.
    
    Returns:
        List of competitor dictionaries
    """
    if config is None:
        config = load_competitor_config()
    return config.get('competitors', [])


def get_assets_for_competitor(competitor_name: str, config: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """
    Get assets for a specific competitor
    
    Args:
        competitor_name: Name of the competitor
        config: Configuration dictionary. If None, loads from default location.
    
    Returns:
        List of asset dictionaries for the competitor
    """
    if config is None:
        config = load_competitor_config()
    
    for competitor in config.get('competitors', []):
        if competitor.get('name') == competitor_name:
            return competitor.get('assets', [])
    
    return []


def get_all_assets(config: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """
    Get all assets from all competitors
    
    Args:
        config: Configuration dictionary. If None, loads from default location.
    
    Returns:
        List of all asset dictionaries with competitor name included
    """
    if config is None:
        config = load_competitor_config()
    
    all_assets = []
    for competitor in config.get('competitors', []):
        competitor_name = competitor.get('name')
        for asset in competitor.get('assets', []):
            asset_with_competitor = asset.copy()
            asset_with_competitor['competitor_name'] = competitor_name
            asset_with_competitor['competitor_base_url'] = competitor.get('base_url')
            all_assets.append(asset_with_competitor)
    
    return all_assets

