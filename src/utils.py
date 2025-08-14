#!/usr/bin/env python3
"""
Utilities and helper functions for the Xtractor application
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

from config.settings import CREDENTIALS_FILE, LOG_FORMAT, LOG_FILE

def setup_logging(level: str = "INFO"):
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=LOG_FORMAT,
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler()
        ]
    )

def load_credentials() -> Dict[str, Any]:
    """Load website credentials from JSON file"""
    try:
        with open(CREDENTIALS_FILE, 'r') as f:
            data = json.load(f)
        
        # Convert to dictionary keyed by website name for easy lookup
        credentials = {}
        for website in data.get('websites', []):
            credentials[website['name']] = website
        
        return credentials
    except Exception as e:
        logging.error(f"Failed to load credentials: {e}")
        return {}

def save_json(data: Any, filepath: Path) -> None:
    """Save data as JSON file"""
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2, default=str)

def load_json(filepath: Path) -> Any:
    """Load data from JSON file"""
    with open(filepath, 'r') as f:
        return json.load(f)

def validate_part_number(part_number: str) -> bool:
    """Validate part number format"""
    if not part_number or len(part_number) < 7:
        return False
    
    # Check for common patterns
    import re
    patterns = [
        r'^\d{4}-\d{3}$',      # 6000-487
        r'^\d{4}-\d{2}$',      # 2015-05
        r'^[A-Z]\d{4}-\d{3}$', # A6000-487
    ]
    
    return any(re.match(pattern, part_number) for pattern in patterns)

def format_price(price: float) -> str:
    """Format price for display"""
    return f"${price:.2f}"

def create_session_id() -> str:
    """Create a unique session identifier"""
    return f"xtractor_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for filesystem compatibility"""
    import re
    # Remove or replace invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    return sanitized.strip()

def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """Split list into chunks of specified size"""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]

def get_file_timestamp(filepath: Path) -> datetime:
    """Get file modification timestamp"""
    return datetime.fromtimestamp(filepath.stat().st_mtime)

def ensure_directory(directory: Path) -> None:
    """Ensure directory exists, create if needed"""
    directory.mkdir(parents=True, exist_ok=True)
