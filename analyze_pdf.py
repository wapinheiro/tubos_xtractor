#!/usr/bin/env python3
"""
PDF Analyzer for Parts Catalog
Analyzes the structure and content of the catalog sample
"""

import pdfplumber
import PyPDF2
import pandas as pd
import re
from pathlib import Path

def analyze_pdf_structure(pdf_path):
    """Analyze the PDF structure and extract sample data"""
    print(f"Analyzing PDF: {pdf_path}")
    print("=" * 50)
    
    # Basic PDF info
    with open(pdf_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        num_pages = len(pdf_reader.pages)
        print(f"Total pages: {num_pages}")
    
    # Detailed analysis with pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        print(f"PDF metadata: {pdf.metadata}")
        print("\n" + "=" * 50)
        
        # Analyze first few pages
        for i, page in enumerate(pdf.pages[:3]):  # First 3 pages
            print(f"\nPage {i+1}:")
            print("-" * 30)
            
            # Extract text
            text = page.extract_text()
            if text:
                lines = text.split('\n')
                print(f"Lines of text: {len(lines)}")
                print("Sample lines:")
                for j, line in enumerate(lines[:10]):  # First 10 lines
                    print(f"  {j+1}: {line.strip()}")
            
            # Look for tables
            tables = page.extract_tables()
            if tables:
                print(f"\nTables found: {len(tables)}")
                for t_idx, table in enumerate(tables):
                    print(f"Table {t_idx+1} - Rows: {len(table)}, Cols: {len(table[0]) if table else 0}")
                    if table:
                        print("Sample rows:")
                        for r_idx, row in enumerate(table[:3]):  # First 3 rows
                            print(f"  Row {r_idx+1}: {row}")
    
    return num_pages

def extract_part_patterns(pdf_path):
    """Look for common part number patterns"""
    print("\nSearching for part number patterns...")
    print("=" * 50)
    
    patterns = [
        r'\b\d{4}-\d{3}\b',  # 6000-487 pattern
        r'\b\d{4}-\d{2}\b',   # 4 digits - 2 digits
        r'\b[A-Z]\d{4}-\d{3}\b', # Letter + digits pattern
        r'\b\d{6}-\d{3}\b',   # 6 digits - 3 digits
    ]
    
    all_matches = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text:
                for pattern in patterns:
                    matches = re.findall(pattern, text)
                    for match in matches:
                        all_matches.append({
                            'page': page_num + 1,
                            'pattern': pattern,
                            'part_number': match
                        })
    
    if all_matches:
        df = pd.DataFrame(all_matches)
        print(f"Found {len(all_matches)} potential part numbers:")
        print(df.groupby('pattern').size())
        print("\nSample matches:")
        print(df.head(10))
    else:
        print("No part number patterns found with standard patterns")
    
    return all_matches

if __name__ == "__main__":
    pdf_path = "media/catalog_sample_10955.pdf"
    
    if Path(pdf_path).exists():
        analyze_pdf_structure(pdf_path)
        extract_part_patterns(pdf_path)
    else:
        print(f"PDF file not found: {pdf_path}")
