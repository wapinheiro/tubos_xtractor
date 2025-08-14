#!/usr/bin/env python3
"""
Price Fetcher for Jacuzzi Dealer Website

Automates the process of fetching pricing information from the Jacuzzi
dealer website for parts extracted from catalogs.
"""

import logging
import time
import re
from datetime import datetime
from typing import List, Tuple, Dict, Any, Optional

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from config.settings import REQUEST_DELAY, MAX_RETRY_ATTEMPTS, SELENIUM_OPTIONS
from config.schemas import Part, ProcessingError, ErrorType, PartStatus
from src.utils import chunk_list

class PriceFetcher:
    """Fetches pricing information from Jacuzzi dealer website"""
    
    def __init__(self, credentials: Dict[str, Any]):
        self.logger = logging.getLogger(__name__)
        self.credentials = credentials
        self.driver = None
        self.is_logged_in = False
    
    def fetch_prices(self, parts: List[Part]) -> Tuple[List[Part], List[ProcessingError]]:
        """
        Fetch prices for a list of parts
        
        Args:
            parts: List of parts to fetch prices for
            
        Returns:
            Tuple of (updated parts, errors)
        """
        self.logger.info(f"Fetching prices for {len(parts)} parts")
        
        updated_parts = []
        errors = []
        
        try:
            # Initialize web driver
            self._setup_driver()
            
            # Login to Jacuzzi dealer site
            if not self._login():
                error = ProcessingError(
                    part_number="ALL",
                    error_type=ErrorType.LOGIN_FAILED,
                    error_message="Failed to login to Jacuzzi dealer website"
                )
                errors.append(error)
                return updated_parts, errors
            
            # Navigate to price lookup page
            if not self._navigate_to_price_lookup():
                error = ProcessingError(
                    part_number="ALL",
                    error_type=ErrorType.NETWORK_ERROR,
                    error_message="Failed to navigate to price lookup page"
                )
                errors.append(error)
                return updated_parts, errors
            
            # Process parts in chunks to avoid overwhelming the server
            chunks = chunk_list(parts, 10)  # Process 10 parts at a time
            
            for chunk_num, chunk in enumerate(chunks, 1):
                self.logger.info(f"Processing chunk {chunk_num}/{len(chunks)}")
                
                for part in chunk:
                    try:
                        price = self._fetch_part_price(part.part_number)
                        if price is not None:
                            part.price = price
                            part.last_price_update = datetime.now()
                            part.status = PartStatus.PRICED
                            updated_parts.append(part)
                            self.logger.debug(f"Found price for {part.part_number}: ${price:.2f}")
                        else:
                            part.status = PartStatus.PRICE_FAILED
                            error = ProcessingError(
                                part_number=part.part_number,
                                error_type=ErrorType.PART_NOT_FOUND,
                                error_message="Part not found in Jacuzzi system",
                                page_reference=part.page_reference
                            )
                            errors.append(error)
                    
                    except Exception as e:
                        self.logger.warning(f"Error fetching price for {part.part_number}: {str(e)}")
                        part.status = PartStatus.PRICE_FAILED
                        error = ProcessingError(
                            part_number=part.part_number,
                            error_type=ErrorType.UNEXPECTED,
                            error_message=str(e),
                            page_reference=part.page_reference
                        )
                        errors.append(error)
                    
                    # Rate limiting
                    time.sleep(REQUEST_DELAY)
                
                # Longer pause between chunks
                if chunk_num < len(chunks):
                    time.sleep(REQUEST_DELAY * 2)
        
        except Exception as e:
            self.logger.error(f"Critical error in price fetching: {str(e)}", exc_info=True)
            error = ProcessingError(
                part_number="ALL",
                error_type=ErrorType.UNEXPECTED,
                error_message=f"Critical error: {str(e)}"
            )
            errors.append(error)
        
        finally:
            self._cleanup_driver()
        
        self.logger.info(f"Price fetching complete: {len(updated_parts)} updated, {len(errors)} errors")
        return updated_parts, errors
    
    def _setup_driver(self) -> None:
        """Initialize Selenium WebDriver"""
        chrome_options = Options()
        for option in SELENIUM_OPTIONS:
            chrome_options.add_argument(option)
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.implicitly_wait(10)
            self.logger.info("WebDriver initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize WebDriver: {str(e)}")
            raise
    
    def _cleanup_driver(self) -> None:
        """Clean up WebDriver resources"""
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("WebDriver cleaned up")
            except:
                pass
            finally:
                self.driver = None
    
    def _login(self) -> bool:
        """Login to Jacuzzi dealer website"""
        try:
            jacuzzi_creds = self.credentials.get('Jacuzzi Dealer')
            if not jacuzzi_creds:
                self.logger.error("Jacuzzi dealer credentials not found")
                return False
            
            self.logger.info("Logging into Jacuzzi dealer website")
            self.driver.get(jacuzzi_creds['url'])
            
            # Wait for login form
            wait = WebDriverWait(self.driver, 15)
            
            # Find and fill username field
            username_field = wait.until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            username_field.clear()
            username_field.send_keys(jacuzzi_creds['username'])
            
            # Find and fill password field
            password_field = self.driver.find_element(By.NAME, "password")
            password_field.clear()
            password_field.send_keys(jacuzzi_creds['password'])
            
            # Submit login form
            login_button = self.driver.find_element(By.XPATH, "//input[@type='submit' or @value='Login']")
            login_button.click()
            
            # Wait for login to complete
            time.sleep(3)
            
            # Check if login was successful
            if "logout" in self.driver.page_source.lower() or "welcome" in self.driver.page_source.lower():
                self.is_logged_in = True
                self.logger.info("Successfully logged into Jacuzzi dealer website")
                return True
            else:
                self.logger.error("Login appears to have failed")
                return False
                
        except TimeoutException:
            self.logger.error("Timeout waiting for login page elements")
            return False
        except Exception as e:
            self.logger.error(f"Error during login: {str(e)}")
            return False
    
    def _navigate_to_price_lookup(self) -> bool:
        """Navigate to the price lookup page"""
        try:
            self.logger.info("Navigating to price lookup page")
            
            # Look for Orders menu
            wait = WebDriverWait(self.driver, 15)
            orders_link = wait.until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Orders"))
            )
            orders_link.click()
            
            # Look for Lookups submenu
            lookups_link = wait.until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Lookups"))
            )
            lookups_link.click()
            
            # Look for Prices option
            prices_link = wait.until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Prices"))
            )
            prices_link.click()
            
            # Wait for price lookup form to load
            wait.until(
                EC.presence_of_element_located((By.NAME, "part_number"))
            )
            
            self.logger.info("Successfully navigated to price lookup page")
            return True
            
        except TimeoutException:
            self.logger.error("Timeout waiting for price lookup page")
            return False
        except Exception as e:
            self.logger.error(f"Error navigating to price lookup: {str(e)}")
            return False
    
    def _fetch_part_price(self, part_number: str) -> Optional[float]:
        """
        Fetch price for a single part number
        
        Args:
            part_number: The part number to look up
            
        Returns:
            Price as float, or None if not found
        """
        try:
            # Find the part number input field
            part_input = self.driver.find_element(By.NAME, "part_number")
            part_input.clear()
            part_input.send_keys(part_number)
            
            # Find and click refresh button
            refresh_button = self.driver.find_element(
                By.XPATH, "//input[@type='submit' and @value='Refresh']"
            )
            refresh_button.click()
            
            # Wait for results table to load
            wait = WebDriverWait(self.driver, 10)
            results_table = wait.until(
                EC.presence_of_element_located((By.TAG_NAME, "table"))
            )
            
            # Parse the results table to find Net Unit Price
            return self._parse_price_from_table(results_table)
            
        except TimeoutException:
            self.logger.warning(f"Timeout waiting for results for part {part_number}")
            return None
        except NoSuchElementException:
            self.logger.warning(f"Could not find required elements for part {part_number}")
            return None
        except Exception as e:
            self.logger.warning(f"Error fetching price for {part_number}: {str(e)}")
            return None
    
    def _parse_price_from_table(self, table_element) -> Optional[float]:
        """
        Parse Net Unit Price from the results table
        
        Args:
            table_element: Selenium WebElement for the table
            
        Returns:
            Price as float, or None if not found
        """
        try:
            # Get all table rows
            rows = table_element.find_elements(By.TAG_NAME, "tr")
            
            if len(rows) < 2:  # Need at least header + one data row
                return None
            
            # Find the header row to identify column positions
            header_row = rows[0]
            headers = [th.text.strip().lower() for th in header_row.find_elements(By.TAG_NAME, "th")]
            
            # Find the Net Unit Price column
            net_price_col = None
            for i, header in enumerate(headers):
                if "net" in header and "price" in header:
                    net_price_col = i
                    break
            
            if net_price_col is None:
                self.logger.warning("Could not find Net Unit Price column")
                return None
            
            # Get the first data row
            data_row = rows[1]
            cells = data_row.find_elements(By.TAG_NAME, "td")
            
            if len(cells) <= net_price_col:
                return None
            
            # Extract price text
            price_text = cells[net_price_col].text.strip()
            
            # Parse price (remove currency symbols, commas, etc.)
            price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
            if price_match:
                return float(price_match.group())
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Error parsing price from table: {str(e)}")
            return None
