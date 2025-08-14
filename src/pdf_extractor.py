#!/usr/bin/env python3
"""
PDF Extractor for Parts Catalogs

Handles parsing of PDF catalogs to extract part information including
part numbers, descriptions, categories, and page references.
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional

import pdfplumber
import PyPDF2
import pandas as pd

from config.settings import PDF_PART_NUMBER_PATTERNS, EXTRACTS_DIR
from config.schemas import Part, CatalogMetadata, PartStatus
from src.utils import save_json, validate_part_number, sanitize_filename

class PDFExtractor:
    """Extracts parts data from PDF catalogs"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def extract_parts(self, pdf_path: str) -> Tuple[List[Part], CatalogMetadata]:
        """
        Extract all parts from a PDF catalog
        
        Args:
            pdf_path: Path to the PDF catalog file
            
        Returns:
            Tuple of (parts list, catalog metadata)
        """
        pdf_path = Path(pdf_path)
        self.logger.info(f"Extracting parts from: {pdf_path}")
        
        # Initialize metadata
        metadata = CatalogMetadata(
            filename=pdf_path.name,
            total_pages=0,
            catalog_version=self._extract_catalog_version(pdf_path),
            catalog_date=self._extract_catalog_date(pdf_path)
        )
        
        parts = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                metadata.total_pages = len(pdf.pages)
                self.logger.info(f"Processing {metadata.total_pages} pages")
                
                for page_num, page in enumerate(pdf.pages, 1):
                    page_parts = self._extract_parts_from_page(page, page_num)
                    parts.extend(page_parts)
                    
                    if page_num % 50 == 0:  # Progress logging
                        self.logger.info(f"Processed {page_num}/{metadata.total_pages} pages, found {len(parts)} parts")
                
                # Post-process parts
                parts = self._deduplicate_parts(parts)
                parts = self._enrich_parts_metadata(parts, pdf_path)
                
                # Update metadata
                metadata.total_parts = len(parts)
                metadata.successful_extractions = len([p for p in parts if p.part_number])
                metadata.failed_extractions = metadata.total_parts - metadata.successful_extractions
                
                self.logger.info(f"Extraction complete: {len(parts)} unique parts found")
                
                # Save extraction data
                self._save_extraction_data(parts, metadata)
                
                return parts, metadata
                
        except Exception as e:
            self.logger.error(f"Error extracting from PDF: {str(e)}", exc_info=True)
            return [], metadata
    
    def _extract_parts_from_page(self, page, page_num: int) -> List[Part]:
        """Extract parts from a single PDF page"""
        parts = []
        
        try:
            # Extract text
            text = page.extract_text()
            if not text:
                return parts
            
            # Look for part numbers using regex patterns
            for pattern in PDF_PART_NUMBER_PATTERNS:
                matches = re.finditer(pattern, text)
                for match in matches:
                    part_number = match.group().strip()
                    
                    # Validate part number
                    if not validate_part_number(part_number):
                        continue
                    
                    # Extract description (text following the part number)
                    description = self._extract_description(text, match.end())
                    
                    # Extract category from page context
                    category = self._extract_category(text, page_num)
                    
                    part = Part(
                        part_number=part_number,
                        description=description,
                        category=category,
                        page_reference=page_num,
                        status=PartStatus.EXTRACTED
                    )
                    
                    parts.append(part)
            
            # Also try to extract from tables if present
            tables = page.extract_tables()
            if tables:
                table_parts = self._extract_parts_from_tables(tables, page_num)
                parts.extend(table_parts)
                
        except Exception as e:
            self.logger.warning(f"Error processing page {page_num}: {str(e)}")
        
        return parts
    
    def _extract_parts_from_tables(self, tables: List, page_num: int) -> List[Part]:
        """Extract parts from table structures on the page"""
        parts = []
        
        for table in tables:
            if not table or len(table) < 2:  # Need header + at least one row
                continue
            
            # Try to identify part number column
            header_row = table[0] if table[0] else []
            part_num_col = self._find_part_number_column(header_row)
            desc_col = self._find_description_column(header_row)
            
            if part_num_col is None:
                continue
            
            # Process data rows
            for row in table[1:]:
                if not row or len(row) <= part_num_col:
                    continue
                
                part_number = str(row[part_num_col]).strip() if row[part_num_col] else ""
                if not validate_part_number(part_number):
                    continue
                
                description = ""
                if desc_col is not None and len(row) > desc_col and row[desc_col]:
                    description = str(row[desc_col]).strip()
                
                part = Part(
                    part_number=part_number,
                    description=description,
                    page_reference=page_num,
                    status=PartStatus.EXTRACTED
                )
                
                parts.append(part)
        
        return parts
    
    def _find_part_number_column(self, header_row: List) -> Optional[int]:
        """Find the column index that likely contains part numbers"""
        if not header_row:
            return None
        
        part_keywords = ['part', 'number', 'item', 'sku', 'code']
        
        for i, header in enumerate(header_row):
            if not header:
                continue
            header_lower = str(header).lower()
            if any(keyword in header_lower for keyword in part_keywords):
                return i
        
        return None
    
    def _find_description_column(self, header_row: List) -> Optional[int]:
        """Find the column index that likely contains descriptions"""
        if not header_row:
            return None
        
        desc_keywords = ['description', 'desc', 'name', 'title']
        
        for i, header in enumerate(header_row):
            if not header:
                continue
            header_lower = str(header).lower()
            if any(keyword in header_lower for keyword in desc_keywords):
                return i
        
        return None
    
    def _extract_description(self, text: str, start_pos: int) -> str:
        """Extract description text following a part number"""
        # Get text after the part number
        remaining_text = text[start_pos:start_pos + 200]  # Limit to next 200 chars
        
        # Split by lines and take the first meaningful line
        lines = remaining_text.split('\n')
        for line in lines:
            line = line.strip()
            if line and len(line) > 5:  # Skip very short lines
                # Clean up the description
                line = re.sub(r'^\W+', '', line)  # Remove leading non-word chars
                line = re.sub(r'\s+', ' ', line)  # Normalize whitespace
                return line[:100]  # Limit length
        
        return ""
    
    def _extract_category(self, text: str, page_num: int) -> str:
        """Extract category information from page context"""
        # Look for common category indicators
        category_patterns = [
            r'(?i)(pumps?|motor|controller|heater|filter|jet|light|cover|spa|tub)',
            r'(?i)(electrical|plumbing|hardware|accessory|part)',
        ]
        
        # Check first few lines of the page for category headers
        lines = text.split('\n')[:10]
        for line in lines:
            for pattern in category_patterns:
                match = re.search(pattern, line)
                if match:
                    return match.group(1).title()
        
        # Default category based on page ranges (rough estimate)
        if page_num < 50:
            return "Accessories"
        elif page_num < 100:
            return "Pumps & Motors"
        elif page_num < 150:
            return "Electrical"
        elif page_num < 200:
            return "Plumbing"
        else:
            return "Hardware"
    
    def _deduplicate_parts(self, parts: List[Part]) -> List[Part]:
        """Remove duplicate parts, keeping the one with the most information"""
        if not parts:
            return parts
        
        # Group by part number
        part_groups = {}
        for part in parts:
            if part.part_number not in part_groups:
                part_groups[part.part_number] = []
            part_groups[part.part_number].append(part)
        
        # Keep the best part from each group
        deduplicated = []
        for part_number, part_list in part_groups.items():
            if len(part_list) == 1:
                deduplicated.append(part_list[0])
            else:
                # Choose the part with the most complete information
                best_part = max(part_list, key=lambda p: len(p.description) + len(p.category))
                deduplicated.append(best_part)
        
        self.logger.info(f"Deduplicated {len(parts)} parts to {len(deduplicated)} unique parts")
        return deduplicated
    
    def _enrich_parts_metadata(self, parts: List[Part], pdf_path: Path) -> List[Part]:
        """Add metadata to parts"""
        catalog_name = pdf_path.stem
        
        for part in parts:
            part.source_catalog = catalog_name
            part.metadata['extraction_date'] = datetime.now().isoformat()
            part.metadata['source_file'] = str(pdf_path)
        
        return parts
    
    def _extract_catalog_version(self, pdf_path: Path) -> str:
        """Extract catalog version from PDF metadata or filename"""
        # Try to extract from filename
        filename = pdf_path.stem
        version_match = re.search(r'(\d{4})', filename)
        if version_match:
            return version_match.group(1)
        
        # Try to extract from PDF content (first page)
        try:
            with pdfplumber.open(pdf_path) as pdf:
                if pdf.pages:
                    text = pdf.pages[0].extract_text()
                    if text:
                        version_match = re.search(r'(\d{4}.*catalog)', text, re.IGNORECASE)
                        if version_match:
                            return version_match.group(1)
        except:
            pass
        
        return "Unknown"
    
    def _extract_catalog_date(self, pdf_path: Path) -> Optional[datetime]:
        """Extract catalog date from PDF metadata"""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                metadata = pdf_reader.metadata
                
                if metadata and '/CreationDate' in metadata:
                    # PDF date format: D:YYYYMMDDHHmmSSOHH'mm'
                    date_str = metadata['/CreationDate']
                    if date_str.startswith('D:'):
                        date_str = date_str[2:10]  # Extract YYYYMMDD
                        return datetime.strptime(date_str, '%Y%m%d')
        except:
            pass
        
        return None
    
    def _save_extraction_data(self, parts: List[Part], metadata: CatalogMetadata) -> None:
        """Save extraction results to disk"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save parts data
        parts_data = [part.to_dict() for part in parts]
        parts_file = EXTRACTS_DIR / f"parts_{sanitize_filename(metadata.filename)}_{timestamp}.json"
        save_json(parts_data, parts_file)
        
        # Save metadata
        metadata_file = EXTRACTS_DIR / f"metadata_{sanitize_filename(metadata.filename)}_{timestamp}.json"
        save_json(metadata.to_dict(), metadata_file)
        
        self.logger.info(f"Saved extraction data to {parts_file}")
        self.logger.info(f"Saved metadata to {metadata_file}")
