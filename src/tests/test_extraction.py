#!/usr/bin/env python3
"""
Test Script for Xtractor PDF Extraction

Tests the PDF extraction functionality with the sample catalog
"""

import sys
from pathlib import Path

# Add src directory to path
sys.path.append(str(Path(__file__).parent / "src"))
sys.path.append(str(Path(__file__).parent))

import logging
from src.utils import setup_logging
from src.pdf_extractor import PDFExtractor

def test_pdf_extraction():
    """Test PDF extraction with sample catalog"""
    setup_logging("INFO")
    logger = logging.getLogger(__name__)
    
    # Path to sample catalog
    catalog_path = "data/catalogs/catalog_sample_10955.pdf"
    
    if not Path(catalog_path).exists():
        logger.error(f"Sample catalog not found: {catalog_path}")
        return False
    
    logger.info("Testing PDF extraction functionality")
    
    try:
        # Initialize extractor
        extractor = PDFExtractor()
        
        # Extract first 10 pages only for testing
        logger.info("Extracting parts from sample catalog (first 10 pages)")
        parts, metadata = extractor.extract_parts(catalog_path)
        
        # Display results
        logger.info(f"Extraction Results:")
        logger.info(f"  Total parts found: {len(parts)}")
        logger.info(f"  Catalog pages: {metadata.total_pages}")
        logger.info(f"  Successful extractions: {metadata.successful_extractions}")
        logger.info(f"  Failed extractions: {metadata.failed_extractions}")
        
        # Show sample parts
        logger.info("\nSample extracted parts:")
        for i, part in enumerate(parts[:10]):  # Show first 10 parts
            logger.info(f"  {i+1}. {part.part_number} - {part.description[:50]}...")
        
        # Show part categories
        categories = {}
        for part in parts:
            categories[part.category] = categories.get(part.category, 0) + 1
        
        logger.info(f"\nParts by category:")
        for category, count in sorted(categories.items()):
            logger.info(f"  {category}: {count} parts")
        
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    success = test_pdf_extraction()
    if success:
        print("\n✅ PDF extraction test completed successfully!")
    else:
        print("\n❌ PDF extraction test failed!")
        sys.exit(1)
