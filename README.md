# Xtractor - Automated Parts Catalog Processing

## Project Structure
```
extractor/
├── main.py                 # Main orchestrator
├── creden.json            # Website credentials
├── config/
│   ├── settings.py        # Configuration settings
│   └── schemas.py         # Data schemas
├── src/
│   ├── pdf_extractor.py   # PDF parsing and part extraction
│   ├── price_fetcher.py   # Jacuzzi pricing automation
│   ├── data_manager.py    # Data processing and CSV generation
│   └── utils.py           # Utilities and helpers
├── data/
│   ├── catalogs/          # Input PDF catalogs
│   ├── extracts/          # Extracted parts data
│   ├── prices/            # Pricing data with timestamps
│   ├── outputs/           # Final CSV files
│   ├── errors/            # Error logs and failed parts
│   └── backups/           # Historical data backups
├── logs/                  # Application logs
└── tests/                 # Unit tests
```

## Solution Architecture

### Phase 1: PDF Extraction
- Parse parts catalog PDF (250 pages, ~4,000 parts)
- Extract: Part Number, Description, Category, Page Reference
- Store in structured format with data validation

### Phase 2: Price Enrichment
- Automate Jacuzzi dealer website
- Batch process part lookups with rate limiting
- Handle errors gracefully (missing parts, network issues)
- Store pricing data with timestamps

### Phase 3: Data Management
- Merge catalog data with pricing data
- Generate CSV for Lou Dashboard upload
- Create error reports for failed lookups
- Maintain backup/historical data

### Phase 4: Monitoring & Maintenance
- Logging and progress tracking
- Partial update capability
- Data freshness validation
- Automated scheduling (3x/week max)

## Lou Dashboard CSV Schema (Proposed)

Based on typical inventory systems and the data flow:

```csv
sku,part_number,description,category,unit_price,last_updated,source_catalog,vendor,status
```

**Field Definitions:**
- `sku`: Internal SKU identifier (generated or existing)
- `part_number`: Manufacturer part number (from catalog)
- `description`: Part description (from catalog)
- `category`: Part category/group (from catalog structure)
- `unit_price`: Net unit price (from Jacuzzi)
- `last_updated`: Timestamp when price was retrieved
- `source_catalog`: Catalog version/date for traceability
- `vendor`: "Jacuzzi" (for multi-vendor support)
- `status`: "active", "discontinued", "price_pending"

## Error Handling Strategy

**Error Types:**
1. **PDF Parsing Errors** - Corrupted pages, unreadable text
2. **Part Not Found** - Part number doesn't exist in Jacuzzi system
3. **Network Errors** - Website timeouts, login failures
4. **Data Validation** - Invalid part numbers, price formats
5. **Rate Limiting** - Too many requests to Jacuzzi site

**Error File Format:**
```csv
part_number,error_type,error_message,timestamp,retry_count,page_reference
```

## Data Freshness & Backup Strategy

**Freshness:**
- Track when each price was last updated
- Flag stale data (>7 days old)
- Support selective updates for recently changed parts

**Backup:**
- Daily snapshots of complete dataset
- Version-controlled catalog extractions
- Historical pricing trends
- Audit trail for all changes

## Implementation Timeline

**Week 1**: Core PDF extraction and data structures
**Week 2**: Jacuzzi website automation and pricing
**Week 3**: CSV generation and error handling
**Week 4**: Testing, validation, and Lou Dashboard integration

Ready to proceed with implementation?
