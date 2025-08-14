#!/usr/bin/env python3
"""
Data schemas and models for the Xtractor application
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

class PartStatus(Enum):
    """Status of a part in the processing pipeline"""
    EXTRACTED = "extracted"          # Extracted from PDF
    PRICE_PENDING = "price_pending"  # Waiting for price lookup
    PRICED = "priced"               # Price successfully retrieved
    PRICE_FAILED = "price_failed"   # Price lookup failed
    ACTIVE = "active"               # Ready for Lou Dashboard
    DISCONTINUED = "discontinued"    # No longer available

class ErrorType(Enum):
    """Types of errors that can occur during processing"""
    PDF_PARSING = "pdf_parsing"
    PART_NOT_FOUND = "part_not_found"
    NETWORK_ERROR = "network_error"
    VALIDATION_ERROR = "validation_error"
    RATE_LIMIT = "rate_limit"
    LOGIN_FAILED = "login_failed"
    UNEXPECTED = "unexpected"

@dataclass
class Part:
    """Represents a single part from the catalog"""
    part_number: str
    description: str = ""
    category: str = ""
    page_reference: int = 0
    status: PartStatus = PartStatus.EXTRACTED
    price: Optional[float] = None
    last_price_update: Optional[datetime] = None
    source_catalog: str = ""
    vendor: str = "Jacuzzi"
    sku: str = ""
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for CSV/JSON export"""
        return {
            'sku': self.sku or self.part_number,
            'part_number': self.part_number,
            'description': self.description,
            'category': self.category,
            'unit_price': self.price,
            'last_updated': self.last_price_update.isoformat() if self.last_price_update else None,
            'source_catalog': self.source_catalog,
            'vendor': self.vendor,
            'status': self.status.value,
            'page_reference': self.page_reference
        }
    
    def is_price_stale(self, days: int = 7) -> bool:
        """Check if price data is stale"""
        if not self.last_price_update:
            return True
        return (datetime.now() - self.last_price_update).days > days

@dataclass
class ProcessingError:
    """Represents an error that occurred during processing"""
    part_number: str
    error_type: ErrorType
    error_message: str
    timestamp: datetime = field(default_factory=datetime.now)
    retry_count: int = 0
    page_reference: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for CSV export"""
        return {
            'part_number': self.part_number,
            'error_type': self.error_type.value,
            'error_message': self.error_message,
            'timestamp': self.timestamp.isoformat(),
            'retry_count': self.retry_count,
            'page_reference': self.page_reference
        }

@dataclass
class CatalogMetadata:
    """Metadata about a processed catalog"""
    filename: str
    total_pages: int
    processing_date: datetime = field(default_factory=datetime.now)
    total_parts: int = 0
    successful_extractions: int = 0
    failed_extractions: int = 0
    catalog_version: str = ""
    catalog_date: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON export"""
        return {
            'filename': self.filename,
            'total_pages': self.total_pages,
            'processing_date': self.processing_date.isoformat(),
            'total_parts': self.total_parts,
            'successful_extractions': self.successful_extractions,
            'failed_extractions': self.failed_extractions,
            'catalog_version': self.catalog_version,
            'catalog_date': self.catalog_date.isoformat() if self.catalog_date else None
        }

@dataclass
class ProcessingSession:
    """Represents a complete processing session"""
    session_id: str
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    catalog_metadata: Optional[CatalogMetadata] = None
    parts_processed: int = 0
    prices_updated: int = 0
    errors_count: int = 0
    output_file: str = ""
    
    def duration(self) -> Optional[float]:
        """Calculate session duration in seconds"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON export"""
        return {
            'session_id': self.session_id,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': self.duration(),
            'parts_processed': self.parts_processed,
            'prices_updated': self.prices_updated,
            'errors_count': self.errors_count,
            'output_file': self.output_file
        }
