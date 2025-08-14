#!/usr/bin/env python3
"""
Xtractor - Automated Parts Catalog Processing Tool

Main orchestrator for the entire extraction and pricing workflow.
Coordinates PDF extraction, price fetching, and CSV generation.
"""

import logging
import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# Add src directory to path
sys.path.append(str(Path(__file__).parent / "src"))

from config.settings import *
from config.schemas import ProcessingSession, CatalogMetadata
from src.pdf_extractor import PDFExtractor
from src.price_fetcher import PriceFetcher
from src.data_manager import DataManager
from src.utils import setup_logging, load_credentials

def setup_session() -> ProcessingSession:
    """Initialize a new processing session"""
    session_id = f"xtractor_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    return ProcessingSession(session_id=session_id)

def process_catalog(catalog_path: str, session: ProcessingSession, 
                   update_prices: bool = True, 
                   force_refresh: bool = False) -> bool:
    """
    Process a complete catalog through the extraction pipeline
    
    Args:
        catalog_path: Path to the PDF catalog file
        session: Current processing session
        update_prices: Whether to fetch prices from Jacuzzi
        force_refresh: Force price updates even for recent data
    
    Returns:
        bool: True if processing completed successfully
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Starting catalog processing: {catalog_path}")
    
    try:
        # Phase 1: Extract parts from PDF
        logger.info("Phase 1: Extracting parts from PDF catalog")
        extractor = PDFExtractor()
        parts, catalog_metadata = extractor.extract_parts(catalog_path)
        
        if not parts:
            logger.error("No parts extracted from catalog")
            return False
        
        session.catalog_metadata = catalog_metadata
        session.parts_processed = len(parts)
        
        logger.info(f"Extracted {len(parts)} parts from catalog")
        
        # Phase 2: Fetch prices (if requested)
        if update_prices:
            logger.info("Phase 2: Fetching prices from Jacuzzi dealer site")
            credentials = load_credentials()
            price_fetcher = PriceFetcher(credentials)
            
            # Filter parts that need price updates
            parts_to_price = []
            if force_refresh:
                parts_to_price = parts
            else:
                parts_to_price = [p for p in parts if p.is_price_stale(PRICE_STALE_DAYS)]
            
            logger.info(f"Updating prices for {len(parts_to_price)} parts")
            
            updated_parts, errors = price_fetcher.fetch_prices(parts_to_price)
            session.prices_updated = len(updated_parts)
            session.errors_count = len(errors)
            
            # Merge updated parts back into main list
            part_dict = {p.part_number: p for p in parts}
            for updated_part in updated_parts:
                part_dict[updated_part.part_number] = updated_part
            parts = list(part_dict.values())
            
            # Save errors
            if errors:
                DataManager.save_errors(errors, session.session_id)
        
        # Phase 3: Generate output files
        logger.info("Phase 3: Generating output files")
        data_manager = DataManager()
        
        # Save complete parts data
        parts_file = data_manager.save_parts_data(parts, session.session_id)
        logger.info(f"Saved parts data to: {parts_file}")
        
        # Generate Lou Dashboard CSV
        csv_file = data_manager.generate_lou_csv(parts, session.session_id)
        session.output_file = str(csv_file)
        logger.info(f"Generated Lou Dashboard CSV: {csv_file}")
        
        # Create backup
        backup_file = data_manager.create_backup(parts, session.session_id)
        logger.info(f"Created backup: {backup_file}")
        
        # Save session metadata
        data_manager.save_session_metadata(session)
        
        logger.info("Catalog processing completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error during catalog processing: {str(e)}", exc_info=True)
        return False

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Xtractor - Automated Parts Catalog Processing")
    parser.add_argument("catalog", help="Path to the PDF catalog file")
    parser.add_argument("--no-prices", action="store_true", 
                       help="Skip price fetching, only extract parts")
    parser.add_argument("--force-refresh", action="store_true",
                       help="Force price updates even for recent data")
    parser.add_argument("--log-level", default="INFO",
                       choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       help="Set logging level")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    # Validate input file
    catalog_path = Path(args.catalog)
    if not catalog_path.exists():
        logger.error(f"Catalog file not found: {catalog_path}")
        sys.exit(1)
    
    if not catalog_path.suffix.lower() == '.pdf':
        logger.error("Input file must be a PDF")
        sys.exit(1)
    
    # Initialize session
    session = setup_session()
    logger.info(f"Starting processing session: {session.session_id}")
    
    # Process catalog
    success = process_catalog(
        str(catalog_path),
        session,
        update_prices=not args.no_prices,
        force_refresh=args.force_refresh
    )
    
    # Finalize session
    session.end_time = datetime.now()
    
    if success:
        logger.info(f"Processing completed successfully in {session.duration():.1f} seconds")
        logger.info(f"Parts processed: {session.parts_processed}")
        logger.info(f"Prices updated: {session.prices_updated}")
        logger.info(f"Errors: {session.errors_count}")
        logger.info(f"Output file: {session.output_file}")
        sys.exit(0)
    else:
        logger.error("Processing failed")
        sys.exit(1)

if __name__ == "__main__":
    main()