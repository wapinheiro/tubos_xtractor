#!/usr/bin/env python3
"""
Configuration settings for the Xtractor application
"""

import os
from pathlib import Path
from datetime import datetime

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

# Directory structure
CATALOGS_DIR = DATA_DIR / "catalogs"
EXTRACTS_DIR = DATA_DIR / "extracts"
PRICES_DIR = DATA_DIR / "prices"
OUTPUTS_DIR = DATA_DIR / "outputs"
ERRORS_DIR = DATA_DIR / "errors"
BACKUPS_DIR = DATA_DIR / "backups"

# Ensure all directories exist
for directory in [CATALOGS_DIR, EXTRACTS_DIR, PRICES_DIR, OUTPUTS_DIR, ERRORS_DIR, BACKUPS_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Credentials file
CREDENTIALS_FILE = BASE_DIR / "creden.json"

# Processing settings
MAX_RETRY_ATTEMPTS = 3
REQUEST_DELAY = 2.0  # Seconds between Jacuzzi requests (rate limiting)
BATCH_SIZE = 50      # Parts to process before saving checkpoint
PRICE_STALE_DAYS = 7 # Days before price is considered stale

# PDF processing settings
PDF_PART_NUMBER_PATTERNS = [
    r'\b\d{4}-\d{3}\b',      # Primary pattern: 6000-487
    r'\b\d{4}-\d{2}\b',      # Secondary pattern: 2015-05
    r'\b[A-Z]\d{4}-\d{3}\b', # Letter prefix pattern: A6000-487
]

# Lou Dashboard CSV schema
LOU_CSV_COLUMNS = [
    'sku',
    'part_number',
    'description', 
    'category',
    'unit_price',
    'last_updated',
    'source_catalog',
    'vendor',
    'status'
]

# Error tracking
ERROR_CSV_COLUMNS = [
    'part_number',
    'error_type',
    'error_message',
    'timestamp',
    'retry_count',
    'page_reference'
]

# Logging configuration
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_FILE = LOGS_DIR / f"xtractor_{datetime.now().strftime('%Y%m%d')}.log"

# Website configuration
WEBSITES = {
    'sundance': {
        'name': 'Sundance Spas support',
        'login_url': 'https://www.sundancesupport.com/index.php',
        'catalog_path': '/technical-training/parts-catalog'
    },
    'jacuzzi': {
        'name': 'Jacuzzi Dealer',
        'login_url': 'http://jacuzzidealerdata.com/',
        'price_lookup_path': '/orders/lookups/prices'
    }
}

# Selenium configuration
SELENIUM_OPTIONS = [
    '--headless',
    '--no-sandbox',
    '--disable-dev-shm-usage',
    '--disable-gpu',
    '--window-size=1920,1080'
]

# Data validation rules
VALIDATION_RULES = {
    'part_number': {
        'min_length': 7,
        'max_length': 15,
        'required_patterns': [r'\d{4}-\d{2,3}']
    },
    'price': {
        'min_value': 0.01,
        'max_value': 10000.00,
        'decimal_places': 2
    }
}
