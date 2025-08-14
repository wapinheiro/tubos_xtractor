#!/usr/bin/env python3
"""
Data Manager for Xtractor Application

Handles data persistence, CSV generation, backup creation, and
data validation for the parts extraction and pricing workflow.
"""

import logging
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

import pandas as pd

from config.settings import (
    LOU_CSV_COLUMNS, ERROR_CSV_COLUMNS, OUTPUTS_DIR, ERRORS_DIR, 
    BACKUPS_DIR, PRICES_DIR, EXTRACTS_DIR
)
from config.schemas import Part, ProcessingError, ProcessingSession, PartStatus
from src.utils import save_json, sanitize_filename, ensure_directory

class DataManager:
    """Manages data persistence and file operations"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Ensure all directories exist
        for directory in [OUTPUTS_DIR, ERRORS_DIR, BACKUPS_DIR, PRICES_DIR, EXTRACTS_DIR]:
            ensure_directory(directory)
    
    def save_parts_data(self, parts: List[Part], session_id: str) -> Path:
        """
        Save parts data as JSON file
        
        Args:
            parts: List of parts to save
            session_id: Unique session identifier
            
        Returns:
            Path to saved file
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"parts_data_{session_id}_{timestamp}.json"
        filepath = EXTRACTS_DIR / filename
        
        # Convert parts to serializable format
        parts_data = {
            'metadata': {
                'session_id': session_id,
                'timestamp': timestamp,
                'total_parts': len(parts),
                'parts_with_prices': len([p for p in parts if p.price is not None])
            },
            'parts': [part.to_dict() for part in parts]
        }
        
        save_json(parts_data, filepath)
        self.logger.info(f"Saved {len(parts)} parts to {filepath}")
        
        return filepath
    
    def generate_lou_csv(self, parts: List[Part], session_id: str) -> Path:
        """
        Generate CSV file for Lou Dashboard upload
        
        Args:
            parts: List of parts to include in CSV
            session_id: Unique session identifier
            
        Returns:
            Path to generated CSV file
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"lou_dashboard_{session_id}_{timestamp}.csv"
        filepath = OUTPUTS_DIR / filename
        
        # Filter parts that are ready for Lou Dashboard
        ready_parts = [p for p in parts if p.status in [PartStatus.PRICED, PartStatus.ACTIVE]]
        
        self.logger.info(f"Generating Lou CSV with {len(ready_parts)} parts")
        
        # Prepare data for CSV
        csv_data = []
        for part in ready_parts:
            row_data = self._prepare_lou_csv_row(part)
            csv_data.append(row_data)
        
        # Write CSV file
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=LOU_CSV_COLUMNS)
            writer.writeheader()
            writer.writerows(csv_data)
        
        self.logger.info(f"Generated Lou CSV: {filepath}")
        
        # Also save as pandas DataFrame for validation
        df = pd.DataFrame(csv_data)
        self._validate_lou_csv(df, filepath)
        
        return filepath
    
    def _prepare_lou_csv_row(self, part: Part) -> Dict[str, Any]:
        """Prepare a single part for Lou CSV format"""
        return {
            'sku': part.sku or part.part_number,
            'part_number': part.part_number,
            'description': part.description[:200] if part.description else "",  # Limit length
            'category': part.category,
            'unit_price': part.price if part.price is not None else "",
            'last_updated': part.last_price_update.isoformat() if part.last_price_update else "",
            'source_catalog': part.source_catalog,
            'vendor': part.vendor,
            'status': part.status.value
        }
    
    def _validate_lou_csv(self, df: pd.DataFrame, filepath: Path) -> None:
        """Validate the generated Lou CSV for data quality"""
        issues = []
        
        # Check for missing required fields
        required_fields = ['sku', 'part_number']
        for field in required_fields:
            missing_count = df[field].isnull().sum()
            if missing_count > 0:
                issues.append(f"{missing_count} rows missing {field}")
        
        # Check for invalid prices
        price_issues = df['unit_price'].apply(
            lambda x: x != "" and (not isinstance(x, (int, float)) or x <= 0)
        ).sum()
        if price_issues > 0:
            issues.append(f"{price_issues} rows with invalid prices")
        
        # Check for duplicate part numbers
        duplicates = df['part_number'].duplicated().sum()
        if duplicates > 0:
            issues.append(f"{duplicates} duplicate part numbers")
        
        # Log validation results
        if issues:
            self.logger.warning(f"CSV validation issues for {filepath}: {', '.join(issues)}")
        else:
            self.logger.info(f"CSV validation passed for {filepath}")
    
    @staticmethod
    def save_errors(errors: List[ProcessingError], session_id: str) -> Path:
        """
        Save processing errors to CSV file
        
        Args:
            errors: List of errors to save
            session_id: Unique session identifier
            
        Returns:
            Path to saved error file
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"errors_{session_id}_{timestamp}.csv"
        filepath = ERRORS_DIR / filename
        
        # Write errors CSV
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=ERROR_CSV_COLUMNS)
            writer.writeheader()
            for error in errors:
                writer.writerow(error.to_dict())
        
        logging.getLogger(__name__).info(f"Saved {len(errors)} errors to {filepath}")
        return filepath
    
    def create_backup(self, parts: List[Part], session_id: str) -> Path:
        """
        Create backup of complete processing session
        
        Args:
            parts: List of parts to backup
            session_id: Unique session identifier
            
        Returns:
            Path to backup file
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"backup_{session_id}_{timestamp}.json"
        filepath = BACKUPS_DIR / filename
        
        # Create comprehensive backup data
        backup_data = {
            'backup_metadata': {
                'session_id': session_id,
                'timestamp': timestamp,
                'total_parts': len(parts),
                'backup_version': '1.0'
            },
            'parts': [part.to_dict() for part in parts],
            'statistics': self._calculate_statistics(parts)
        }
        
        save_json(backup_data, filepath)
        self.logger.info(f"Created backup: {filepath}")
        
        return filepath
    
    def _calculate_statistics(self, parts: List[Part]) -> Dict[str, Any]:
        """Calculate statistics for the parts data"""
        total_parts = len(parts)
        parts_with_prices = len([p for p in parts if p.price is not None])
        parts_by_status = {}
        
        for status in PartStatus:
            count = len([p for p in parts if p.status == status])
            parts_by_status[status.value] = count
        
        # Price statistics
        prices = [p.price for p in parts if p.price is not None]
        price_stats = {}
        if prices:
            price_stats = {
                'min_price': min(prices),
                'max_price': max(prices),
                'avg_price': sum(prices) / len(prices),
                'total_value': sum(prices)
            }
        
        return {
            'total_parts': total_parts,
            'parts_with_prices': parts_with_prices,
            'price_coverage': (parts_with_prices / total_parts * 100) if total_parts > 0 else 0,
            'parts_by_status': parts_by_status,
            'price_statistics': price_stats
        }
    
    def save_session_metadata(self, session: ProcessingSession) -> Path:
        """
        Save session metadata
        
        Args:
            session: Processing session to save
            
        Returns:
            Path to saved metadata file
        """
        filename = f"session_{session.session_id}.json"
        filepath = EXTRACTS_DIR / filename
        
        save_json(session.to_dict(), filepath)
        self.logger.info(f"Saved session metadata: {filepath}")
        
        return filepath
    
    def load_previous_parts(self, catalog_name: str) -> List[Part]:
        """
        Load parts from previous extraction of the same catalog
        
        Args:
            catalog_name: Name of the catalog to search for
            
        Returns:
            List of previously extracted parts
        """
        # Find the most recent extraction file for this catalog
        pattern = f"parts_*{sanitize_filename(catalog_name)}*.json"
        extraction_files = list(EXTRACTS_DIR.glob(pattern))
        
        if not extraction_files:
            return []
        
        # Sort by modification time, get most recent
        latest_file = max(extraction_files, key=lambda f: f.stat().st_mtime)
        
        try:
            with open(latest_file, 'r') as f:
                data = json.load(f)
            
            parts = []
            for part_data in data.get('parts', []):
                part = Part(
                    part_number=part_data['part_number'],
                    description=part_data.get('description', ''),
                    category=part_data.get('category', ''),
                    page_reference=part_data.get('page_reference', 0),
                    price=part_data.get('unit_price'),
                    source_catalog=part_data.get('source_catalog', ''),
                    vendor=part_data.get('vendor', 'Jacuzzi'),
                    sku=part_data.get('sku', ''),
                    status=PartStatus(part_data.get('status', 'extracted'))
                )
                
                # Parse last_price_update if present
                if part_data.get('last_updated'):
                    try:
                        part.last_price_update = datetime.fromisoformat(part_data['last_updated'])
                    except:
                        pass
                
                parts.append(part)
            
            self.logger.info(f"Loaded {len(parts)} parts from previous extraction: {latest_file}")
            return parts
            
        except Exception as e:
            self.logger.warning(f"Error loading previous parts from {latest_file}: {str(e)}")
            return []
    
    def get_stale_parts(self, parts: List[Part], days: int = 7) -> List[Part]:
        """
        Get parts with stale pricing data
        
        Args:
            parts: List of parts to check
            days: Number of days to consider as stale
            
        Returns:
            List of parts with stale prices
        """
        return [part for part in parts if part.is_price_stale(days)]
