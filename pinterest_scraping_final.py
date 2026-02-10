#!/usr/bin/env python3
"""
Pinterest Image Scraper - OPTIMIZED with:
- BATCH PROCESSING (parallel downloads)
- PERSISTENT URL STORAGE (JSON file to track all scraped URLs across sessions)
- PIN PAGE LINK EXTRACTION (visit pin pages to find original images)
- ALL KEYWORDS EXECUTED (no target limit per keyword)
- SINGLE FOLDER for all images
"""

import os
import time
import re
import hashlib
import json
from io import BytesIO
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Set, Optional, Tuple

import requests
from PIL import Image

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# ============================================
# CONFIG
# ============================================

OUTPUT_FOLDER = "scraped_data/pinterest_jubba"  # Single folder for all images
PERSISTENT_URLS_FILE = "scraped_data/jubba_seen_urls.json"  # Stores all scraped URLs

IMAGES_PER_KEYWORD = None  # None = collect as many as possible per keyword
MAX_SCROLLS_PER_KEYWORD = 10  # Maximum scrolls per keyword before moving to next

MIN_WIDTH = 500
MIN_HEIGHT = 500

SCROLL_PAUSE = 5  # Reduced for faster scrolling
SCROLL_STEP = 5   # Scroll more at once

HEADLESS = True

REQUEST_TIMEOUT = 15  # Reduced timeout
POLITE_DELAY = 0.05   # Reduced delay for faster processing

# Batch processing
MAX_WORKERS = 8  # Number of parallel download threads
BATCH_SIZE = 50  # Process images in batches

# Pin page exploration
VISIT_PIN_PAGES = True  # Enable pin page link extraction
MAX_PIN_PAGES = 20       # Visit up to 5 pin pages per scroll batch

STAGNATION_LIMIT = 5  # Increase before switching keyword

JUBBA_THOBE_KEYWORDS = [
    # Basic Terms
    "Men's Jubba",
    "Men's Thobe", 
    "Men's Jubbah",
    "Men's Thawb",
    "Jubba for men",
    "Thobe for men",
    "Male Jubba",
    "Male Thobe",
    "Mens Jubba",
    "Mens Thobe",
    "Boys Jubba",
    "Boys Thobe",
    "Islamic Robe Men",
    "Muslim Dress Men",
    "Arab Robe Men",
    
    # Alternative Spellings & Names
    "Jubbah Men",
    "Thawb Men",
    "Thoub Men",
    "Dishdasha Men",
    "Kandura Men",
    "Kandora Men",
    "Jalabiya Men",
    "Galabiya Men",
    "Djellaba Men",
    "Gandoura Men",
    "Kaftan Men",
    "Qamis Men",
    "Kamis Men",
    "Gamis Men",
    "Kanzu Men",
    "Long Islamic Dress Men",
    "Arabian Thobe Men",
    "Arabic Dress Men",
    
    # Regional Styles - Gulf States
    "Saudi Thobe Men",
    "Saudi Style Thobe Men",
    "Emirati Kandura Men",
    "UAE Thobe Men",
    "Dubai Style Thobe Men",
    "Qatari Thobe Men",
    "Kuwaiti Dishdasha Men",
    "Omani Thobe Men",
    "Omani Dishdasha Men",
    "Bahraini Thobe Men",
    "Gulf Style Thobe Men",
    "Khaleeji Thobe Men",
    "Arabian Peninsula Thobe",
    
    # Regional Styles - North Africa
    "Moroccan Djellaba Men",
    "Moroccan Jubba Men",
    "Egyptian Galabiya Men",
    "Egyptian Jalabiya Men",
    "Sudanese Jalabiya Men",
    "Libyan Thobe Men",
    "Tunisian Jebba Men",
    "Algerian Gandoura Men",
    "North African Robe Men",
    "Maghribi Thobe Men",
    
    # Regional Styles - South Asia & Southeast Asia
    "Pakistani Jubba Men",
    "Bangladeshi Jubba Men",
    "Indian Jubba Men",
    "Afghan Perahan Tunban Men",
    "Malaysian Jubba Men",
    "Indonesian Gamis Men",
    "Turkish Jubba Men",
    "Central Asian Jubba Men",
    
    # Design Features
    "Embroidered Jubba Men",
    "Embroidered Thobe Men",
    "Designer Thobe Men",
    "Designer Jubba Men",
    "Luxury Thobe Men",
    "Premium Jubba Men",
    "Plain Thobe Men",
    "Simple Jubba Men",
    "Elegant Thobe Men",
    "Royal Jubba Men",
    "Hand Embroidered Thobe Men",
    "Machine Embroidery Jubba Men",
    "Contrast Piping Thobe Men",
    "Contrast Collar Jubba Men",
    "Decorative Stitching Thobe Men",
    "Beaded Jubba Men",
    "Sequin Thobe Men",
    "Mirror Work Jubba Men",
    
    # Collar & Neckline Styles
    "Mandarin Collar Thobe Men",
    "Chinese Collar Jubba Men",
    "Band Collar Thobe Men",
    "Round Neck Jubba Men",
    "V Neck Thobe Men",
    "Stand Collar Jubba Men",
    "Shirt Collar Thobe Men",
    "Collarless Thobe Men",
    "Button Neck Jubba Men",
    "Zip Neck Thobe Men",
    "Omani Collar Thobe Men",
    "Emirati Collar Kandura Men",
    
    # Sleeve Styles
    "Long Sleeve Thobe Men",
    "Full Sleeve Jubba Men",
    "Short Sleeve Thobe Men",
    "Half Sleeve Jubba Men",
    "Three Quarter Sleeve Thobe Men",
    "Cuffed Sleeve Jubba Men",
    "Button Cuff Thobe Men",
    "French Cuff Jubba Men",
    "Wide Sleeve Thobe Men",
    
    # Style Categories
    "Modern Thobe Men",
    "Traditional Jubba Men",
    "Contemporary Thobe Men",
    "Classic Jubba Men",
    "Formal Thobe Men",
    "Casual Jubba Men",
    "Semi Formal Thobe Men",
    "Elegant Jubba Men",
    "Stylish Thobe Men",
    "Trendy Jubba Men",
    "Fashionable Thobe Men",
    "Urban Jubba Men",
    "Minimalist Thobe Men",
    "Islamic Thobe Men",
    "Modest Wear Men Thobe",
    "Ethnic Jubba Men",
    
    # Color Variations
    "White Thobe Men",
    "White Jubba Men",
    "Black Thobe Men",
    "Black Jubba Men",
    "Grey Thobe Men",
    "Gray Jubba Men",
    "Navy Blue Thobe Men",
    "Blue Jubba Men",
    "Brown Thobe Men",
    "Beige Jubba Men",
    "Cream Thobe Men",
    "Off White Jubba Men",
    "Maroon Thobe Men",
    "Green Jubba Men",
    "Olive Thobe Men",
    "Khaki Jubba Men",
    "Charcoal Thobe Men",
    "Ivory Jubba Men",
    "Golden Thobe Men",
    "Silver Jubba Men",
    "Two Tone Thobe Men",
    "Camel Color Jubba Men",
    "Striped Thobe Men",
    "Printed Jubba Men",
    "Solid Color Thobe Men",
    
    # Fabric Types
    "Cotton Thobe Men",
    "Cotton Jubba Men",
    "Polyester Thobe Men",
    "Poly Cotton Jubba Men",
    "Linen Thobe Men",
    "Linen Jubba Men",
    "Silk Thobe Men",
    "Silk Jubba Men",
    "Wool Blend Thobe Men",
    "Mixed Fabric Jubba Men",
    "Premium Cotton Thobe Men",
    "Egyptian Cotton Jubba Men",
    "Japanese Fabric Thobe Men",
    "Soft Fabric Jubba Men",
    "Breathable Thobe Men",
    "Lightweight Jubba Men",
    "Heavy Fabric Thobe Men",
    "Viscose Jubba Men",
    "Spun Polyester Thobe Men",
    
    # Seasonal
    "Summer Thobe Men",
    "Summer Jubba Men",
    "Winter Thobe Men",
    "Winter Jubba Men",
    "All Season Thobe Men",
    "Lightweight Thobe Men",
    "Warm Jubba Men",
    "Cool Thobe Men",
    "Hot Weather Jubba Men",
    "Cold Weather Thobe Men",
    
    # Occasions
    "Eid Thobe Men",
    "Eid Jubba Men",
    "Ramadan Thobe Men",
    "Ramadan Jubba Men",
    "Jummah Thobe Men",
    "Friday Prayer Jubba Men",
    "Wedding Thobe Men",
    "Wedding Jubba Men",
    "Hajj Thobe Men",
    "Umrah Jubba Men",
    "Nikah Thobe Men",
    "Walima Jubba Men",
    "Engagement Thobe Men",
    "Festival Jubba Men",
    "Party Wear Thobe Men",
    "Ceremonial Jubba Men",
    "Religious Thobe Men",
    "Mosque Wear Jubba Men",
    "Prayer Thobe Men",
    "Islamic Prayer Jubba Men",
    
    # Special Occasions - Eid
    "Eid Mubarak Thobe Men",
    "Eid Collection Jubba Men",
    "Eid Special Thobe Men",
    "Eid ul Fitr Jubba Men",
    "Eid ul Adha Thobe Men",
    "New Eid Thobe Design Men",
    
    # Special Occasions - Ramadan
    "Ramadan Special Jubba Men",
    "Ramadan Collection Thobe Men",
    "Taraweeh Jubba Men",
    "Iftar Thobe Men",
    "Sahur Jubba Men",
    
    # Fashion Trends
    "Thobe Fashion Men 2026",
    "Latest Jubba Design Men",
    "New Thobe Style Men",
    "Trending Jubba Men",
    "Modern Thobe Design Men",
    "Latest Thobe Fashion Men",
    "Contemporary Islamic Wear Men",
    "Jubba Trends 2026",
    "Fashion Thawb Men",
    "Streetwear Jubba Men",
    
    # Fit & Cut
    "Slim Fit Thobe Men",
    "Slim Fit Jubba Men",
    "Regular Fit Thobe Men",
    "Regular Fit Jubba Men",
    "Loose Fit Thobe Men",
    "Tailored Jubba Men",
    "Custom Fit Thobe Men",
    "Fitted Jubba Men",
    "Comfortable Fit Thobe Men",
    "Relaxed Fit Jubba Men",
    "Straight Cut Thobe Men",
    "Athletic Fit Jubba Men",
    "Modern Fit Thobe Men",
    
    # Length Variations
    "Long Thobe Men",
    "Long Jubba Men",
    "Ankle Length Thobe Men",
    "Ankle Length Jubba Men",
    "Floor Length Thobe Men",
    "Full Length Jubba Men",
    "Above Ankle Thobe Men",
    "Short Jubba Men",
    
    # Pattern & Style Details
    "Plain Thobe Men",
    "Plain Jubba Men",
    "Solid Color Thobe Men",
    "Textured Jubba Men",
    "Jacquard Thobe Men",
    "Two Tone Jubba Men",
    "Contrast Collar Thobe Men",
    "Contrast Stitch Jubba Men",
    "Minimalist Thobe Men",
    "Decorative Thobe Men",
    
    # Age Groups
    "Adult Men Thobe",
    "Adult Men Jubba",
    "Young Men Thobe",
    "Young Men Jubba",
    "Teen Thobe Men",
    "Boys Jubba",
    "Kids Thobe",
    "Father Son Thobe Set",
    "Father Son Jubba Set",
    "Matching Thobe Set",
    "Family Jubba Set",
    
    # Sets & Combinations
    "Thobe Set Men",
    "Jubba Set Men",
    "Thobe with Kufi Men",
    "Jubba with Cap Men",
    "Thobe with Sirwal Men",
    "Jubba with Pants Men",
    "Complete Islamic Outfit Men",
    "Thobe Pajama Set Men",
    "Jubba with Izaar Men",
    
    # Accessories Related
    "Thobe with Ghutra Men",
    "Jubba with Turban Men",
    "Thobe with Shemagh Men",
    "Jubba with Scarf Men",
    "Thobe with Agal Men",
    "Jubba with Bisht Men",
    "Kandura with Tarboosh Men",
    "Thobe with Waistcoat Men",
    
    # Brand & Quality Terms
    "Branded Thobe Men",
    "Branded Jubba Men",
    "Premium Quality Thobe Men",
    "High Quality Jubba Men",
    "Exclusive Thobe Men",
    "Luxury Jubba Men",
    "Designer Islamic Wear Men",
    "Handcrafted Thobe Men",
    "Artisan Jubba Men",
    "Boutique Thobe Men",
    "Authentic Arab Thobe Men",
    
    # Shopping Related
    "Buy Thobe Men Online",
    "Buy Jubba Men Online",
    "Thobe Men Shopping",
    "Jubba Men Shopping",
    "Affordable Thobe Men",
    "Affordable Jubba Men",
    "Cheap Thobe Men",
    "Budget Jubba Men",
    "Discount Thobe Men",
    "Sale Jubba Men",
    "Best Thobe Men",
    "Best Jubba Men",
    "Custom Thobe Online",
    "Thobe Sale Men",
    
    # Style Inspiration
    "Thobe Outfit Men",
    "Jubba Look Men",
    "Thobe Style Ideas Men",
    "How to Wear Jubba Men",
    "Thobe Styling Men",
    "Jubba Fashion Tips Men",
    "Islamic Fashion Men",
    "Muslim Men Fashion",
    "Arab Street Style Thobe",
    "Modern Islamic Style Men",
    
    # Cultural & Traditional
    "Traditional Islamic Dress Men",
    "Traditional Arab Dress Men",
    "Ethnic Wear Men Thobe",
    "Cultural Dress Men Middle East",
    "Modest Islamic Clothing Men",
    "Sunnah Clothing Men",
    "Islamic Traditional Wear Men",
    "Gulf Traditional Dress Men",
    "Middle Eastern Men Dress",
    "South Asian Islamic Wear Men",
    
    # Specific Design Elements
    "Thobe with Pocket Men",
    "Jubba with Side Pocket Men",
    "Button Down Thobe Men",
    "Zip Front Jubba Men",
    "Hidden Button Thobe Men",
    "Front Opening Jubba Men",
    "Side Slit Thobe Men",
    "Tassel Thobe Men",
    "Hidden Placket Jubba Men",
    "Double Pocket Thobe Men",
    
    # Religious & Spiritual
    "Prayer Thobe Men",
    "Prayer Jubba Men",
    "Salah Thobe Men",
    "Namaz Jubba Men",
    "Islamic Prayer Dress Men",
    "Mosque Attire Men",
    "Religious Clothing Men",
    "Pious Wear Men",
    "Imam Thobe Men",
    "Scholar Jubba Men",
    
    # Special Features
    "Wrinkle Free Thobe Men",
    "Wrinkle Free Jubba Men",
    "Easy Care Thobe Men",
    "No Iron Jubba Men",
    "Quick Dry Thobe Men",
    "Stain Resistant Jubba Men",
    "Comfortable Thobe Men",
    "Soft Fabric Jubba Men",
    "Anti-Static Thobe Men",
    "Fade Resistant Jubba Men",
    
    # Professional & Formal
    "Office Wear Thobe Men",
    "Professional Jubba Men",
    "Business Thobe Men",
    "Smart Casual Jubba Men",
    "Formal Islamic Wear Men",
    "Executive Thobe Men",
    "Corporate Jubba Men",
    
    # Combination Searches
    "Thobe and Sandals Men",
    "Jubba and Sneakers Men",
    "Islamic Outfit Men",
    "Muslim Men Thobe",
    "Arab Traditional Jubba",
    "Middle Eastern Dress Men",
    "Modest Men Clothing",
    "Halal Fashion Men",
    
    # Additional Specific Terms
    "Groom Thobe Men",
    "Groom Jubba Men",
    "Bridegroom Islamic Dress",
    "Best Man Thobe",
    "Groomsmen Jubba",
    "Wedding Party Thobe Men",
    "Ceremonial Islamic Dress Men",
]


class PersistentURLStore:
    """Manages persistent storage of seen URLs across sessions"""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.seen_urls: Set[str] = set()
        self.saved_hashes: Set[str] = set()
        self._load()
    
    def _load(self):
        """Load seen URLs from JSON file"""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.seen_urls = set(data.get('seen_urls', []))
                    self.saved_hashes = set(data.get('saved_hashes', []))
                print(f"📂 Loaded {len(self.seen_urls)} seen URLs and {len(self.saved_hashes)} hashes from cache")
            except Exception as e:
                print(f"⚠️ Could not load URL cache: {e}")
        else:
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
    
    def save(self):
        """Save seen URLs to JSON file"""
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump({
                    'seen_urls': list(self.seen_urls),
                    'saved_hashes': list(self.saved_hashes)
                }, f, indent=2)
            print(f"💾 Saved {len(self.seen_urls)} URLs to cache")
        except Exception as e:
            print(f"⚠️ Could not save URL cache: {e}")
    
    def add_url(self, url: str):
        self.seen_urls.add(url)
    
    def add_hash(self, hash_str: str):
        self.saved_hashes.add(hash_str)
    
    def has_url(self, url: str) -> bool:
        return url in self.seen_urls
    
    def has_hash(self, hash_str: str) -> bool:
        return hash_str in self.saved_hashes


class ImageDownloader:
    """Handles batch image downloading"""
    
    def __init__(self, headers: dict, timeout: int, min_width: int, min_height: int):
        self.headers = headers
        self.timeout = timeout
        self.min_width = min_width
        self.min_height = min_height
    
    def download_and_validate(self, url: str) -> Optional[Tuple[bytes, int, int, str]]:
        """
        Download image and validate dimensions.
        Returns: (content, width, height, extension) or None
        """
        try:
            r = requests.get(url, headers=self.headers, timeout=self.timeout)
            r.raise_for_status()
            content = r.content
            
            if not content or len(content) < 1024:
                return None
            
            # Get dimensions
            try:
                im = Image.open(BytesIO(content))
                w, h = im.size
            except Exception:
                return None
            
            if w < self.min_width or h < self.min_height:
                return None
            
            # Determine extension
            ext = ".jpg"
            ct = (r.headers.get("Content-Type") or "").lower()
            if "png" in ct:
                ext = ".png"
            elif "webp" in ct:
                ext = ".webp"
            elif "gif" in ct:
                ext = ".gif"
            
            return (content, w, h, ext)
        
        except Exception:
            return None


class PinterestScraper:
    def __init__(
        self,
        keywords,
        output_folder,
        persistent_store: PersistentURLStore,
        images_per_keyword=None,
        max_scrolls_per_keyword=100,
        min_width=700,
        min_height=700,
        scroll_pause=2,
        scroll_step=3,
        headless=False,
        stagnation_limit=8,
        max_workers=8,
        batch_size=50,
        visit_pin_pages=True,
        max_pin_pages=5,
    ):
        self.keywords = keywords[:]
        self.output_folder = output_folder
        self.store = persistent_store
        
        self.images_per_keyword = images_per_keyword  # None = unlimited
        self.max_scrolls_per_keyword = max_scrolls_per_keyword
        self.min_width = min_width
        self.min_height = min_height
        
        self.scroll_pause = scroll_pause
        self.scroll_step = scroll_step
        self.headless = headless
        self.stagnation_limit = stagnation_limit
        
        self.max_workers = max_workers
        self.batch_size = batch_size
        self.visit_pin_pages = visit_pin_pages
        self.max_pin_pages = max_pin_pages
        
        self.driver = None
        self.total_stored_count = 0  # Total across all keywords
        self.keyword_stored_count = 0  # Count for current keyword
        
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Referer": "https://www.pinterest.com/",
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        }
        
        self.downloader = ImageDownloader(
            self.headers, REQUEST_TIMEOUT, self.min_width, self.min_height
        )
        
        self._last_seen_urls_count = 0
        self._stagnant_ticks = 0
        
        self.keyword_index = 0
        self.keyword = None
        
        # Create single output folder
        os.makedirs(self.output_folder, exist_ok=True)
        
        # Keyword statistics
        self.keyword_stats = {}

    def setup_driver(self):
        print("⚙️  Setting up Chrome WebDriver...")
        
        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--window-size=1920,1080")
        options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_experimental_option("prefs", {
            "profile.default_content_setting_values.notifications": 2,
            "profile.default_content_settings.popups": 0,
        })
        
        self.driver = webdriver.Chrome(options=options)
        
        try:
            self.driver.execute_cdp_cmd("Network.setUserAgentOverride", {
                "userAgent": self.headers["User-Agent"]
            })
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
        except Exception:
            pass
        
        print("✅ WebDriver ready!\n")

    def open_pinterest_for_keyword(self, keyword):
        self.keyword = keyword
        self.keyword_stored_count = 0  # Reset counter for new keyword
        
        query = quote(self.keyword)
        url = f"https://www.pinterest.com/search/pins/?q={query}"
        
        print("\n" + "=" * 70)
        print(f"🔎 Keyword [{self.keyword_index + 1}/{len(self.keywords)}]: {self.keyword}")
        print(f"🌐 Opening: {url}")
        print(f"📁 Saving to: {self.output_folder}")
        print("=" * 70)
        
        self.driver.get(url)
        time.sleep(4)
        
        # Close popups
        try:
            close_buttons = self.driver.find_elements(By.CSS_SELECTOR, '[aria-label="Close"]')
            for btn in close_buttons:
                try:
                    btn.click()
                    time.sleep(0.3)
                except Exception:
                    pass
        except Exception:
            pass
        
        self._last_seen_urls_count = len(self.store.seen_urls)
        self._stagnant_ticks = 0

    def scroll_chunk(self, times=3):
        for _ in range(times):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(self.scroll_pause)

    def _normalize_and_upgrade_url(self, url: str) -> str:
        if not url:
            return url
        url = url.split("?")[0].strip()
        for size in ("/236x/", "/474x/", "/564x/", "/736x/"):
            if size in url:
                url = url.replace(size, "/originals/")
                break
        return url

    def _url_from_img_element(self, img):
        try:
            src = img.get_attribute("src")
            if src and "pinimg.com" in src:
                return self._normalize_and_upgrade_url(src)
            
            data_src = img.get_attribute("data-src")
            if data_src and "pinimg.com" in data_src:
                return self._normalize_and_upgrade_url(data_src)
            
            srcset = img.get_attribute("srcset")
            if srcset and "pinimg.com" in srcset:
                found = re.findall(r"(https://[^\s,]+)", srcset)
                if found:
                    return self._normalize_and_upgrade_url(found[-1])
        except Exception:
            pass
        return None

    def extract_image_elements(self):
        try:
            css = 'img[src*="pinimg.com"], img[srcset*="pinimg.com"], img[data-src*="pinimg.com"]'
            return self.driver.find_elements(By.CSS_SELECTOR, css)
        except Exception:
            return []

    def extract_pin_page_links(self) -> list:
        """Extract Pinterest pin page links (e.g., /pin/123456/)"""
        try:
            links = self.driver.find_elements(By.CSS_SELECTOR, 'a[href*="/pin/"]')
            pin_links = []
            for link in links:
                href = link.get_attribute("href")
                if href and "/pin/" in href and href not in pin_links:
                    pin_links.append(href)
                if len(pin_links) >= self.max_pin_pages:
                    break
            return pin_links
        except Exception:
            return []

    def visit_pin_page_for_images(self, pin_url: str) -> list:
        """
        Visit a pin page and extract high-resolution image URLs.
        Returns list of image URLs found on that page.
        """
        found_urls = []
        original_window = self.driver.current_window_handle
        
        try:
            # Open in new tab
            self.driver.execute_script(f"window.open('{pin_url}', '_blank');")
            time.sleep(1)
            
            # Switch to new tab
            all_windows = self.driver.window_handles
            for window in all_windows:
                if window != original_window:
                    self.driver.switch_to.window(window)
                    break
            
            time.sleep(2)  # Wait for page load
            
            # Extract images from pin page
            img_elements = self.extract_image_elements()
            for img in img_elements:
                url = self._url_from_img_element(img)
                if url and not self.store.has_url(url):
                    found_urls.append(url)
            
            # Close tab and switch back
            self.driver.close()
            self.driver.switch_to.window(original_window)
            
        except Exception as e:
            # If error, try to recover
            try:
                self.driver.switch_to.window(original_window)
            except Exception:
                pass
        
        return found_urls

    def collect_urls_batch(self) -> list:
        """
        Collect a batch of unique image URLs from current page.
        Optionally visits pin pages to find more images.
        """
        urls = []
        
        # 1. Extract direct image URLs
        img_elements = self.extract_image_elements()
        for img in img_elements:
            url = self._url_from_img_element(img)
            if url and not self.store.has_url(url):
                urls.append(url)
                self.store.add_url(url)
        
        # 2. Visit pin pages for more images
        if self.visit_pin_pages and len(urls) < self.batch_size:
            pin_links = self.extract_pin_page_links()
            if pin_links:
                print(f"🔗 Found {len(pin_links)} pin page links, visiting...")
            
            for pin_link in pin_links:
                pin_urls = self.visit_pin_page_for_images(pin_link)
                for url in pin_urls:
                    if not self.store.has_url(url):
                        urls.append(url)
                        self.store.add_url(url)
                
                time.sleep(0.5)  # Polite delay between pin visits
        
        return urls

    def process_batch(self, urls: list):
        """
        Process a batch of URLs in parallel using ThreadPoolExecutor.
        """
        if not urls:
            return
        
        print(f"🚀 Processing batch of {len(urls)} URLs with {self.max_workers} workers...")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all download tasks
            future_to_url = {
                executor.submit(self.downloader.download_and_validate, url): url
                for url in urls
            }
            
            # Process completed downloads
            for future in as_completed(future_to_url):
                # Check if we should stop for this keyword
                if self.images_per_keyword and self.keyword_stored_count >= self.images_per_keyword:
                    break
                
                url = future_to_url[future]
                
                try:
                    result = future.result()
                    
                    if result is None:
                        continue
                    
                    content, w, h, ext = result
                    
                    # Check content hash
                    content_hash = hashlib.md5(content).hexdigest()
                    if self.store.has_hash(content_hash):
                        continue
                    
                    # Save image to SINGLE folder
                    self.store.add_hash(content_hash)
                    self.keyword_stored_count += 1
                    self.total_stored_count += 1
                    
                    # Filename includes keyword for identification
                    safe_keyword = self.keyword.replace(' ', '_').replace("'", "").replace("'", "")
                    filename = f"{safe_keyword}_{self.total_stored_count:05d}_{w}x{h}{ext}"
                    filepath = os.path.join(self.output_folder, filename)
                    
                    with open(filepath, "wb") as f:
                        f.write(content)
                    
                    print(f"✅ [Total: {self.total_stored_count} | Keyword: {self.keyword_stored_count}] Saved: {filename}")
                    
                except Exception as e:
                    continue

    def _update_stagnation(self):
        current = len(self.store.seen_urls)
        if current == self._last_seen_urls_count:
            self._stagnant_ticks += 1
        else:
            self._stagnant_ticks = 0
            self._last_seen_urls_count = current
        return self._stagnant_ticks

    def scrape_keyword(self, keyword):
        """Scrape images for a single keyword"""
        self.open_pinterest_for_keyword(keyword)
        
        scrolls_done = 0
        keyword_start_count = self.total_stored_count
        
        while True:
            # Check scroll limit for this keyword
            if scrolls_done >= self.max_scrolls_per_keyword:
                print(f"⚠️ Reached max scrolls ({self.max_scrolls_per_keyword}) for keyword '{keyword}'")
                break
            
            # Check if we have target images for this keyword
            if self.images_per_keyword and self.keyword_stored_count >= self.images_per_keyword:
                print(f"✅ Reached target of {self.images_per_keyword} images for keyword '{keyword}'")
                break
            
            # Collect URLs in batch
            batch_urls = self.collect_urls_batch()
            
            # Process batch in parallel
            if batch_urls:
                self.process_batch(batch_urls)
            
            # Scroll for more content
            self.scroll_chunk(times=self.scroll_step)
            scrolls_done += self.scroll_step
            
            stagnant_ticks = self._update_stagnation()
            
            print(
                f"📌 Keyword Progress: [{self.keyword_index + 1}/{len(self.keywords)}] "
                f"keyword_images={self.keyword_stored_count} | "
                f"total_images={self.total_stored_count} | "
                f"scrolls={scrolls_done}/{self.max_scrolls_per_keyword} | "
                f"stagnant={stagnant_ticks}/{self.stagnation_limit}"
            )
            
            # Check stagnation
            if stagnant_ticks >= self.stagnation_limit:
                print(f"⚠️ No new URLs found for {self.stagnation_limit} ticks. Moving to next keyword.")
                break
            
            # Save progress periodically
            if self.total_stored_count % 50 == 0:
                self.store.save()
        
        # Store keyword stats
        self.keyword_stats[keyword] = {
            'images_collected': self.keyword_stored_count,
            'scrolls': scrolls_done
        }
        
        print(f"\n🎯 Keyword '{keyword}' completed: {self.keyword_stored_count} images collected\n")

    def run(self):
        try:
            self.setup_driver()
            
            if not self.keywords:
                print("❌ No keywords provided.")
                return
            
            # Process ALL keywords one by one
            for idx, keyword in enumerate(self.keywords):
                self.keyword_index = idx
                self.scrape_keyword(keyword)
                
                # Small delay between keywords
                time.sleep(2)
            
            # Final summary
            print("\n" + "=" * 70)
            print("🎉 ALL KEYWORDS COMPLETED!")
            print("=" * 70)
            print(f"Total images collected:  {self.total_stored_count}")
            print(f"Total URLs seen:         {len(self.store.seen_urls)}")
            print(f"Unique hashes saved:     {len(self.store.saved_hashes)}")
            print(f"Keywords processed:      {len(self.keywords)}")
            print(f"Output folder:           {self.output_folder}")
            print("\n📊 Per-Keyword Statistics:")
            print("-" * 70)
            for kw, stats in self.keyword_stats.items():
                print(f"  • {kw}: {stats['images_collected']} images ({stats['scrolls']} scrolls)")
            print("=" * 70 + "\n")
        
        except KeyboardInterrupt:
            print("\n\n⚠️ Interrupted by user!")
            print(f"Progress: {self.total_stored_count} images collected so far")
        
        finally:
            # Save final state
            self.store.save()
            
            if self.driver:
                try:
                    self.driver.quit()
                except Exception:
                    pass


def main():
    print("\n" + "=" * 70)
    print("🎨 PINTEREST SCRAPER - ALL KEYWORDS MODE")
    print("   ✓ Processes ALL keywords (no total limit)")
    print("   ✓ Single output folder for all images")
    print("   ✓ Batch processing with parallel downloads")
    print("   ✓ Persistent URL storage (no duplicates)")
    print("   ✓ Pin page link exploration")
    print("=" * 70)
    print(f"Keywords:               {len(JUBBA_THOBE_KEYWORDS)}")
    print(f"Output Folder:          {OUTPUT_FOLDER} (SINGLE FOLDER)")
    print(f"URL Cache:              {PERSISTENT_URLS_FILE}")
    print(f"Images per keyword:     {'UNLIMITED' if IMAGES_PER_KEYWORD is None else IMAGES_PER_KEYWORD}")
    print(f"Max scrolls/keyword:    {MAX_SCROLLS_PER_KEYWORD}")
    print(f"Min Size:               {MIN_WIDTH}x{MIN_HEIGHT}")
    print(f"Workers:                {MAX_WORKERS}")
    print(f"Batch Size:             {BATCH_SIZE}")
    print(f"Visit Pin Pages:        {VISIT_PIN_PAGES} (max {MAX_PIN_PAGES} per batch)")
    print(f"Stagnation Limit:       {STAGNATION_LIMIT}")
    print(f"Headless:               {HEADLESS}")
    print("=" * 70 + "\n")
    
    # Initialize persistent store
    store = PersistentURLStore(PERSISTENT_URLS_FILE)
    
    scraper = PinterestScraper(
        keywords=JUBBA_THOBE_KEYWORDS,
        output_folder=OUTPUT_FOLDER,
        persistent_store=store,
        images_per_keyword=IMAGES_PER_KEYWORD,
        max_scrolls_per_keyword=MAX_SCROLLS_PER_KEYWORD,
        min_width=MIN_WIDTH,
        min_height=MIN_HEIGHT,
        scroll_pause=SCROLL_PAUSE,
        scroll_step=SCROLL_STEP,
        headless=HEADLESS,
        stagnation_limit=STAGNATION_LIMIT,
        max_workers=MAX_WORKERS,
        batch_size=BATCH_SIZE,
        visit_pin_pages=VISIT_PIN_PAGES,
        max_pin_pages=MAX_PIN_PAGES,
    )
    scraper.run()
    print("Done.\n")


if __name__ == "__main__":
    main()
