#!/usr/bin/env python3
"""
Pinterest Image Scraper - HI-RES + TARGET COUNT + DEDUPE + VISUAL HIGHLIGHTING
+ KEYWORD ROTATION WHEN STAGNANT + SINGLE FOLDER WITH SEQUENTIAL NAMING

Modified to:
- Save all images in a single folder (no keyword subfolders)
- Name images sequentially as 1.jpg, 2.jpg, 3.jpg, etc.
- Resume numbering from existing files if script is restarted
"""

import os
import time
import re
import hashlib
from io import BytesIO
from urllib.parse import quote

import requests
from PIL import Image

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options


# ============================================
# CONFIG
# ============================================

# All images will go here directly (no subfolders)
OUTPUT_FOLDER = "data_raw/pinterest_downloads"

TOTAL_IMAGES = 2000

MIN_WIDTH = 700
MIN_HEIGHT = 700

SCROLL_PAUSE = 3
SCROLL_STEP = 2
MAX_SCROLLS = 5000

HEADLESS = False

REQUEST_TIMEOUT = 25
POLITE_DELAY = 0.15

# If seen_urls doesn't increase for this many progress ticks -> switch keyword
STAGNATION_LIMIT = 5

# Keywords rotation (your existing list)
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


# ============================================


class PinterestScraper:
    def __init__(
        self,
        keywords,
        output_folder,
        total_images=2000,
        min_width=1080,
        min_height=720,
        scroll_pause=3,
        scroll_step=2,
        max_scrolls=5000,
        headless=False,
        stagnation_limit=5,
    ):
        self.keywords = keywords[:]  # copy
        self.output_folder = output_folder

        self.total_images = total_images
        self.min_width = min_width
        self.min_height = min_height

        self.scroll_pause = scroll_pause
        self.scroll_step = scroll_step
        self.max_scrolls = max_scrolls
        self.headless = headless
        self.stagnation_limit = stagnation_limit

        self.driver = None

        # GLOBAL dedupe across all keywords:
        self.seen_urls = set()
        self.saved_hashes = set()

        # Create single output folder and check for existing files
        os.makedirs(self.output_folder, exist_ok=True)
        existing_files = [f for f in os.listdir(self.output_folder) 
                         if os.path.isfile(os.path.join(self.output_folder, f))]
        
        # Find the highest number in existing files to resume correctly
        max_num = 0
        for f in existing_files:
            try:
                # Remove extension and try to parse int
                name_no_ext = os.path.splitext(f)[0]
                num = int(name_no_ext)
                if num > max_num:
                    max_num = num
            except ValueError:
                pass
        
        self.stored_count = max_num
        if max_num > 0:
            print(f"📂 Found {max_num} existing images. Resuming counter from {max_num + 1}.")

        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Referer": "https://www.pinterest.com/",
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        }

        # Stagnation tracking
        self._last_seen_urls_count = 0
        self._stagnant_ticks = 0

        # Current keyword state
        self.keyword_index = 0
        self.keyword = None

    # ---------------------------
    # Driver / navigation
    # ---------------------------
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

        # small stealth-ish tweaks
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
        # Note: No longer creating keyword-specific subfolders

        query = quote(self.keyword)
        url = f"https://www.pinterest.com/search/pins/?q={query}"

        print("\n" + "=" * 70)
        print(f"🔎 Switching to keyword: {self.keyword}")
        print(f"🌐 Opening: {url}")
        print(f"📁 Saving into: {self.output_folder}")
        print("=" * 70)

        self.driver.get(url)
        time.sleep(6)

        # close popups if any
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

        # reset stagnation counters for the new keyword page
        self._last_seen_urls_count = len(self.seen_urls)
        self._stagnant_ticks = 0

    # ---------------------------
    # Scrolling
    # ---------------------------
    def scroll_chunk(self, times=2):
        for _ in range(times):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(self.scroll_pause)

    # ---------------------------
    # URL extraction from img
    # ---------------------------
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

    # ---------------------------
    # Visual highlighting (unchanged)
    # ---------------------------
    def _scroll_into_view(self, el):
        try:
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block:'center', inline:'center'});", el
            )
        except Exception:
            pass

    def _apply_style(self, el, color, label):
        try:
            self._scroll_into_view(el)
            self.driver.execute_script(
                """
                const el = arguments[0];
                const color = arguments[1];
                const label = arguments[2];

                el.style.outline = `5px solid ${color}`;
                el.style.outlineOffset = "2px";
                el.style.boxShadow = `0 0 0 4px rgba(255,255,255,0.85), 0 0 0 10px ${color}55`;
                el.style.borderRadius = "12px";
                el.style.position = (getComputedStyle(el).position === "static") ? "relative" : el.style.position;
                el.style.zIndex = "999999";

                let badge = el.querySelector(":scope > .gs_badge");
                if (!badge) {
                    badge = document.createElement("div");
                    badge.className = "gs_badge";
                    badge.style.position = "absolute";
                    badge.style.top = "8px";
                    badge.style.left = "8px";
                    badge.style.zIndex = "1000000";
                    badge.style.padding = "6px 10px";
                    badge.style.borderRadius = "999px";
                    badge.style.fontFamily = "Arial, sans-serif";
                    badge.style.fontSize = "12px";
                    badge.style.fontWeight = "800";
                    badge.style.letterSpacing = "0.3px";
                    badge.style.color = "#fff";
                    badge.style.boxShadow = "0 2px 10px rgba(0,0,0,0.35)";
                    el.appendChild(badge);
                }
                badge.textContent = label;
                badge.style.background = color;
                """,
                el,
                color,
                label,
            )
        except Exception:
            pass

    def _get_container(self, img):
        try:
            return img.find_element(By.XPATH, "./ancestor::div[1]")
        except Exception:
            return None

    def highlight_processing(self, img):
        c = self._get_container(img)
        if c:
            self._apply_style(c, "dodgerblue", "PROCESSING")
        self._apply_style(img, "dodgerblue", "PROCESSING")

    def highlight_saved(self, img, w, h):
        c = self._get_container(img)
        label = f"SAVED {w}x{h}"
        if c:
            self._apply_style(c, "limegreen", label)
        self._apply_style(img, "limegreen", label)

    def highlight_skipped(self, img, reason):
        c = self._get_container(img)
        if c:
            self._apply_style(c, "crimson", reason)
        self._apply_style(img, "crimson", reason)

    # ---------------------------
    # Image checks + saving
    # ---------------------------
    def _get_dimensions(self, content_bytes):
        try:
            im = Image.open(BytesIO(content_bytes))
            return im.size
        except Exception:
            return None, None

    def process_visible_images(self):
        img_elements = self.extract_image_elements()
        if not img_elements:
            return

        for img in img_elements:
            if self.stored_count >= self.total_images:
                return

            url = self._url_from_img_element(img)
            if not url:
                continue

            if url in self.seen_urls:
                continue
            self.seen_urls.add(url)

            self.highlight_processing(img)

            try:
                r = requests.get(url, headers=self.headers, timeout=REQUEST_TIMEOUT)
                r.raise_for_status()
                content = r.content

                if not content or len(content) < 1024:
                    self.highlight_skipped(img, "SKIPPED TINY")
                    continue

                content_hash = hashlib.md5(content).hexdigest()
                if content_hash in self.saved_hashes:
                    self.highlight_skipped(img, "DUPLICATE")
                    continue

                w, h = self._get_dimensions(content)
                if not w or not h:
                    self.highlight_skipped(img, "BAD IMAGE")
                    continue

                if w < self.min_width or h < self.min_height:
                    self.highlight_skipped(img, f"SMALL {w}x{h}")
                    continue

                # Save with sequential numbering
                self.saved_hashes.add(content_hash)
                self.stored_count += 1

                ext = ".jpg"
                ct = (r.headers.get("Content-Type") or "").lower()
                if "png" in ct:
                    ext = ".png"
                elif "webp" in ct:
                    ext = ".webp"
                elif "gif" in ct:
                    ext = ".gif"

                # MODIFIED: Simple sequential filename
                filename = f"{self.stored_count}{ext}"
                filepath = os.path.join(self.output_folder, filename)

                with open(filepath, "wb") as f:
                    f.write(content)

                self.highlight_saved(img, w, h)
                print(f"✅ Saved {self.stored_count}/{self.total_images}: {filename} ({w}x{h}) from '{self.keyword}'")
                time.sleep(POLITE_DELAY)

            except Exception:
                self.highlight_skipped(img, "FAILED")
                continue

    # ---------------------------
    # Stagnation detection + keyword switching (unchanged)
    # ---------------------------
    def _update_stagnation(self):
        current = len(self.seen_urls)
        if current == self._last_seen_urls_count:
            self._stagnant_ticks += 1
        else:
            self._stagnant_ticks = 0
            self._last_seen_urls_count = current

        return self._stagnant_ticks

    def _next_keyword(self):
        self.keyword_index += 1
        if self.keyword_index >= len(self.keywords):
            return None
        return self.keywords[self.keyword_index]

    # ---------------------------
    # Main loop (unchanged)
    # ---------------------------
    def run(self):
        try:
            self.setup_driver()

            if not self.keywords:
                print("❌ No keywords provided.")
                return

            self.keyword_index = 0
            self.open_pinterest_for_keyword(self.keywords[self.keyword_index])

            scrolls_done = 0

            while self.stored_count < self.total_images:
                if scrolls_done >= self.max_scrolls:
                    print("⚠️ Reached MAX_SCROLLS safety limit. Stopping.")
                    break

                self.process_visible_images()

                if self.stored_count >= self.total_images:
                    break

                self.scroll_chunk(times=self.scroll_step)
                scrolls_done += self.scroll_step

                stagnant_ticks = self._update_stagnation()

                print(
                    f"📌 Progress: stored={self.stored_count}/{self.total_images} | "
                    f"seen_urls={len(self.seen_urls)} | scrolls={scrolls_done}/{self.max_scrolls} | "
                    f"keyword='{self.keyword}' | stagnant={stagnant_ticks}/{self.stagnation_limit}"
                )

                if stagnant_ticks >= self.stagnation_limit:
                    nxt = self._next_keyword()
                    if not nxt:
                        print("⚠️ No more keywords left. Stopping.")
                        break

                    self.open_pinterest_for_keyword(nxt)

            print("\n" + "=" * 70)
            print("📊 FINISHED")
            print(f"Stored total:   {self.stored_count}/{self.total_images}")
            print(f"Seen URLs:      {len(self.seen_urls)}")
            print(f"Unique saved:   {len(self.saved_hashes)}")
            print(f"Last keyword:   {self.keyword}")
            print(f"Output folder:  {self.output_folder}")
            print("=" * 70 + "\n")

        except KeyboardInterrupt:
            print("\n\n⚠️ Interrupted by user!")

        finally:
            if self.driver:
                try:
                    self.driver.quit()
                except Exception:
                    pass


def main():
    print("\n" + "=" * 70)
    print("🎨 PINTEREST SCRAPER (SINGLE FOLDER + SEQUENTIAL NAMING)")
    print("=" * 70)
    print(f"Keywords:       {len(JUBBA_THOBE_KEYWORDS)}")
    print(f"Output Folder:  {OUTPUT_FOLDER}")
    print(f"Target Images:  {TOTAL_IMAGES}")
    print(f"Min Size:       {MIN_WIDTH}x{MIN_HEIGHT}")
    print(f"Naming:         Sequential (1.jpg, 2.jpg, 3.jpg, ...)")
    print(f"Stagnation:     {STAGNATION_LIMIT} ticks without new seen_urls -> switch keyword")
    print(f"Headless:       {HEADLESS}")
    print("=" * 70 + "\n")

    scraper = PinterestScraper(
        keywords=JUBBA_THOBE_KEYWORDS,
        output_folder=OUTPUT_FOLDER,
        total_images=TOTAL_IMAGES,
        min_width=MIN_WIDTH,
        min_height=MIN_HEIGHT,
        scroll_pause=SCROLL_PAUSE,
        scroll_step=SCROLL_STEP,
        max_scrolls=MAX_SCROLLS,
        headless=HEADLESS,
        stagnation_limit=STAGNATION_LIMIT,
    )
    scraper.run()
    print("Done.\n")


if __name__ == "__main__":
    main()
