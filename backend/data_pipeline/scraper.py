"""
Data Scraper
============
Fetches content from URLs and saves raw data
Supports both simple HTTP requests and Selenium for JavaScript-rendered sites
"""

import os
import json
import hashlib
import csv
import time
import random
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from urllib.parse import urlparse

import httpx
from trafilatura import fetch_url, extract
from tqdm import tqdm

from data_pipeline.logger import setup_pipeline_logger

# Optional Selenium support
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    HAS_SELENIUM = True
except ImportError:
    HAS_SELENIUM = False


class DataScraper:
    """
    Scrapes content from URLs defined in sources.csv
    Saves raw content with metadata for processing
    Supports both simple HTTP and Selenium for JavaScript sites
    """

    def __init__(self, base_dir: str = None):
        if base_dir is None:
            base_dir = Path(__file__).parent.parent / "data"
        self.base_dir = Path(base_dir)
        self.raw_dir = self.base_dir / "raw"
        self.sources_file = self.base_dir / "kaso_data_sources.csv"
        self.status_file = self.base_dir / "scrape_status.json"

        # Setup logger
        self.logger = setup_pipeline_logger("scraper")

        # Create directories
        self.raw_dir.mkdir(parents=True, exist_ok=True)

        # Selenium driver (initialized on demand)
        self.driver = None

        # Rotating user agents for stealth
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
        ]

        # Sites that need Selenium (JavaScript-heavy or anti-bot protection)
        self.selenium_required = [
            'linkedin.com',
            'glassdoor.com',
            'crunchbase.com',
            'pitchbook.com',
            'medium.com',
        ]

        # Sites to skip (require login)
        self.skip_sites = [
            'linkedin.com/in/',
            'play.google.com',
            'apps.apple.com',
        ]
    
    def load_sources(self) -> List[Dict]:
        """Load URL sources from CSV file"""
        sources = []

        if not self.sources_file.exists():
            self.logger.warning(f"Sources file not found: {self.sources_file}")
            return sources
        
        with open(self.sources_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Handle different column names
                url = row.get('الروابط') or row.get('url') or row.get('URL') or ''
                source_id = row.get('المصادر') or row.get('id') or ''
                
                if url and url.startswith('http'):
                    sources.append({
                        'id': source_id,
                        'url': url.strip()
                    })
        
        return sources
    
    def load_status(self) -> Dict:
        """Load scraping status from JSON file"""
        if self.status_file.exists():
            with open(self.status_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def save_status(self, status: Dict):
        """Save scraping status"""
        with open(self.status_file, 'w', encoding='utf-8') as f:
            json.dump(status, f, indent=2, ensure_ascii=False)
    
    def get_url_hash(self, url: str) -> str:
        """Generate a unique hash for URL"""
        return hashlib.md5(url.encode()).hexdigest()[:12]

    def _should_skip(self, url: str) -> bool:
        """Check if URL should be skipped (requires login)"""
        return any(skip in url for skip in self.skip_sites)

    def _needs_selenium(self, url: str) -> bool:
        """Check if URL needs Selenium for JavaScript rendering"""
        domain = urlparse(url).netloc.lower()
        return any(site in domain for site in self.selenium_required)

    def _init_selenium(self):
        """Initialize Selenium WebDriver with stealth configuration"""
        if not HAS_SELENIUM:
            return False

        if self.driver is not None:
            return True

        try:
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument(f'--user-agent={random.choice(self.user_agents)}')
            options.add_argument('--window-size=1920,1080')

            # Stealth mode: hide automation flags
            options.add_experimental_option('excludeSwitches', ['enable-automation'])
            options.add_experimental_option('useAutomationExtension', False)

            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)

            # Additional stealth: mask webdriver property
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    })
                '''
            })

            self.logger.info("Selenium WebDriver initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Selenium initialization failed: {e}")
            return False

    def _fetch_with_selenium(self, url: str) -> Optional[str]:
        """Fetch page content using Selenium"""
        if not self._init_selenium():
            return None

        try:
            self.driver.get(url)

            # Wait for page load
            time.sleep(3)

            # Wait for body element
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except:
                pass

            # Scroll to load lazy content
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(1)

            return self.driver.page_source

        except Exception as e:
            self.logger.debug(f"Selenium fetch failed: {e}")
            return None

    def close(self):
        """Clean up Selenium driver"""
        if self.driver:
            self.driver.quit()
            self.driver = None

    def scrape_url(self, url: str) -> Optional[Dict]:
        """
        Scrape content from a single URL with automatic fallback

        Strategy:
        1. Check if URL should be skipped (login required)
        2. Try Selenium first (best results, handles JavaScript)
        3. Fallback to trafilatura if Selenium fails or unavailable

        Returns dict with:
        - url: Original URL
        - title: Page title
        - content: Extracted text content
        - method: 'selenium' or 'trafilatura'
        - scraped_at: Timestamp
        """

        # Skip login-required sites
        if self._should_skip(url):
            return None

        downloaded = None
        method = 'selenium'

        # Try Selenium first if available (best results)
        if HAS_SELENIUM:
            html = self._fetch_with_selenium(url)
            if html:
                downloaded = html
                method = 'selenium'

        # Fallback to trafilatura if:
        # 1. Selenium not available
        # 2. Selenium failed
        # 3. Content is too short (likely blocked/failed)
        if not downloaded or (downloaded and len(downloaded) < 1000):
            try:
                self.logger.debug("Trying trafilatura as fallback...")
                downloaded_traf = fetch_url(url)
                if downloaded_traf:
                    downloaded = downloaded_traf
                    method = 'trafilatura'
            except Exception as e:
                self.logger.debug(f"trafilatura fallback failed: {e}")

        if not downloaded:
            return None

        # Extract content
        try:
            content = extract(
                downloaded,
                include_comments=False,
                include_tables=True,
                include_links=False,
                output_format='txt'
            )

            if not content or len(content.strip()) < 100:
                return None

            # Try to get title
            title = ""
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(downloaded, 'lxml')
                if soup.title:
                    title = soup.title.string or ""
            except:
                pass

            # Get domain as fallback title
            if not title:
                parsed = urlparse(url)
                title = parsed.netloc

            return {
                'url': url,
                'title': title.strip(),
                'content': content.strip(),
                'method': method,
                'scraped_at': datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Error extracting content from {url}: {e}")
            return None
    
    def scrape_all(self, force: bool = False, delay_range: tuple = (1, 3)) -> int:
        """
        Scrape all sources with random delays for stealth

        Args:
            force: If True, re-scrape even if already done
            delay_range: Tuple of (min, max) seconds to wait between requests

        Returns:
            Number of successfully scraped URLs
        """
        sources = self.load_sources()
        status = self.load_status()

        if not sources:
            self.logger.warning("No sources to scrape")
            return 0

        self.logger.info(f"Starting scrape of {len(sources)} URLs")
        self.logger.info(f"Selenium available: {HAS_SELENIUM}")
        self.logger.info(f"Force re-scrape: {force}")

        success_count = 0
        failed_count = 0

        try:
            for source in tqdm(sources, desc="Scraping"):
                url = source['url']
                url_hash = self.get_url_hash(url)

                # Skip if already scraped (unless force)
                if not force and url_hash in status and status[url_hash].get('success'):
                    self.logger.debug(f"Skipping (already scraped): {url}")
                    success_count += 1
                    continue

                # Scrape
                self.logger.info(f"Scraping: {url}")
                result = self.scrape_url(url)

                if result:
                    # Save content
                    output_file = self.raw_dir / f"{url_hash}.json"
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(result, f, indent=2, ensure_ascii=False)

                    # Update status
                    status[url_hash] = {
                        'url': url,
                        'success': True,
                        'method': result.get('method', 'unknown'),
                        'scraped_at': result['scraped_at'],
                        'file': str(output_file.name)
                    }
                    success_count += 1
                    self.logger.info(f"  SUCCESS ({result['method']}): {len(result['content'])} chars")
                else:
                    status[url_hash] = {
                        'url': url,
                        'success': False,
                        'error': 'Failed to extract content'
                    }
                    failed_count += 1
                    self.logger.warning(f"  FAILED: Could not scrape {url}")

                # Save status after each URL to allow resuming and to record methods/errors
                self.save_status(status)

                # Random delay to appear natural
                if delay_range:
                    delay = random.uniform(*delay_range)
                    time.sleep(delay)

        finally:
            # Clean up Selenium driver
            self.close()

        self.logger.info("=" * 70)
        self.logger.info(f"SCRAPING COMPLETE")
        self.logger.info(f"  Success: {success_count}/{len(sources)}")
        self.logger.info(f"  Failed: {failed_count}/{len(sources)}")
        self.logger.info("=" * 70)
        # Summary printed above; return success_count for downstream pipeline steps
        return success_count


def main():
    """CLI entry point
    Parses --force flag and invokes scrape_all. Use alongside run_pipeline.py.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Scrape data from sources")
    parser.add_argument('--force', action='store_true', help="Force re-scrape all URLs")
    args = parser.parse_args()
    
    scraper = DataScraper()
    scraper.scrape_all(force=args.force)


if __name__ == "__main__":
    main()
