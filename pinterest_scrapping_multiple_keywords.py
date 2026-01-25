#!/usr/bin/env python3
"""
Pinterest Image Scraper - HI-RES + TARGET COUNT + DEDUPE + VISUAL HIGHLIGHTING
+ KEYWORD ROTATION WHEN STAGNANT

Adds:
- KEYWORDS list
- Auto-switch keyword when seen_urls stops increasing for N progress prints
- Keeps uniqueness across ALL keywords (content hash + URL)
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

# Keywords rotation (your list)
BURKHA_HIJAB_KEYWORDS = [
    # Basic Terms
    "Burkha with Hijab",
    "Burqa with Hijab", 
    "Burka with Hijab",
    "Abaya with Hijab",
    "Women's Burkha",
    "Ladies Burkha Hijab",
    "Islamic Burkha Hijab",
    "Muslim Women Burkha",
    "Burkha Hijab Set",
    "Complete Burkha Set",
    "Modest Burkha Hijab",
    "Full Coverage Burkha",
    
    # Alternative Names & Spellings
    "Borka with Hijab",
    "Borkha Design",
    "Jilbab with Hijab",
    "Khimar with Burkha",
    "Niqab Burkha Set",
    "Pardha with Hijab",
    "Islamic Dress Women",
    "Modest Gown Hijab",
    "Muslim Dress Set",
    
    # Regional Styles - Middle East (Dubai/Saudi/Gulf)
    "Dubai Style Burkha",
    "Dubai Abaya with Hijab",
    "Saudi Style Burkha",
    "Arabian Burkha Design",
    "Gulf Style Burkha Hijab",
    "Emirati Abaya Style",
    "Khaleeji Burkha Hijab",
    "UAE Burkha Fashion",
    "Dubai Cherry Burkha",
    "Luxury Dubai Abaya",
    
    # Regional Styles - Turkey & Europe
    "Turkish Style Burkha",
    "Turkish Abaya Coat",
    "Istanbul Fashion Burkha",
    "Turkish Hijab Style",
    "Modern Turkish Abaya",
    "European Style Modest Wear",
    
    # Regional Styles - South Asia
    "Bangladeshi Borka Design",
    "New Borka Design BD",
    "Pakistani Burkha Hijab",
    "Indian Burkha Design",
    "Bengali Burkha Style",
    "Desi Burkha Hijab",
    "Kerala Style Pardha",
    "Afghan Style Burkha",
    "South Asian Burkha",
    
    # Regional Styles - Other
    "Indonesian Burkha Hijab",
    "Malaysian Abaya Style",
    "Egyptian Burkha Design",
    "Moroccan Style Burkha",
    "Iranian Chador Style",
    
    # Design Features & Embellishments
    "Embroidered Burkha Hijab",
    "Stone Work Burkha",
    "Pearl Work Abaya",
    "Lace Work Burkha",
    "Bead Work Abaya",
    "Crystal Work Burkha",
    "Sequin Burkha Hijab",
    "Hand Embroidered Burkha",
    "Machine Embroidery Burkha",
    "Rhinestone Burkha",
    "Mirror Work Abaya",
    "Thread Work Burkha",
    "Patchwork Burkha Design",
    
    # Cuts & Silhouettes
    "Butterfly Style Burkha",
    "Butterfly Abaya Hijab",
    "Kaftan Style Burkha",
    "Kimono Style Burkha",
    "Umbrella Cut Burkha",
    "A-Line Burkha Hijab",
    "Princess Cut Burkha",
    "Flared Burkha Hijab",
    "Straight Cut Burkha",
    "Front Open Burkha",
    "Closed Front Burkha",
    "Coat Style Burkha",
    "Gown Style Burkha",
    "Cape Style Abaya",
    "Double Layer Burkha",
    
    # Sleeve Styles
    "Bell Sleeve Burkha",
    "Butterfly Sleeve Burkha",
    "Wide Sleeve Abaya",
    "Cuff Sleeve Burkha",
    "Balloon Sleeve Abaya",
    "Kimono Sleeve Burkha",
    "Elastic Sleeve Borka",
    "Fitted Sleeve Burkha",
    "Flared Sleeve Abaya",
    
    # Opening & Closure Styles
    "Zipper Burkha Hijab",
    "Button Front Burkha",
    "Pull Over Burkha",
    "Overhead Burkha Hijab",
    "Slip On Burkha",
    "Tie Front Burkha",
    
    # Style Categories
    "Modern Burkha Design",
    "Contemporary Burkha Hijab",
    "Traditional Burkha Hijab",
    "Classic Burkha Design",
    "Stylish Burkha Hijab",
    "Trendy Abaya Design",
    "Fashionable Burkha",
    "Elegant Abaya Hijab",
    "Designer Burkha Collection",
    "Boutique Style Abaya",
    "Luxury Burkha Hijab",
    "Premium Burkha Design",
    "Simple Burkha Design",
    "Minimalist Abaya",
    "Casual Burkha Hijab",
    "Formal Burkha Design",
    "Party Wear Burkha",
    
    # Color Variations
    "Black Burkha Hijab",
    "Navy Blue Burkha",
    "Royal Blue Abaya",
    "Maroon Burkha Hijab",
    "Burgundy Abaya",
    "Green Burkha Design",
    "Olive Green Abaya",
    "Brown Burkha Hijab",
    "Beige Burkha Design",
    "Grey Burkha Hijab",
    "White Abaya Hijab",
    "Off White Burkha",
    "Cream Burkha Design",
    "Nude Color Abaya",
    "Dusty Pink Burkha",
    "Purple Burkha Hijab",
    "Peach Abaya Design",
    "Mustard Burkha",
    "Coffee Color Abaya",
    "Mauve Burkha Design",
    "Teal Burkha Hijab",
    "Multi Color Burkha",
    "Two Tone Abaya",
    "Contrast Color Burkha",
    
    # Pattern & Print Types
    "Plain Burkha Hijab",
    "Solid Color Burkha",
    "Printed Burkha Design",
    "Floral Print Abaya",
    "Geometric Print Burkha",
    "Abstract Print Abaya",
    "Striped Burkha Hijab",
    "Polka Dot Burkha",
    "Embossed Burkha Design",
    
    # Fabric Types
    "Dubai Cherry Burkha",
    "Nida Fabric Abaya",
    "Georgette Burkha Hijab",
    "Crepe Burkha Design",
    "Chiffon Abaya Hijab",
    "Jersey Burkha Design",
    "Silk Abaya Hijab",
    "Satin Burkha Design",
    "Velvet Burkha Hijab",
    "Cotton Burkha Design",
    "Linen Abaya Hijab",
    "Modal Burkha Design",
    "Rayon Abaya Hijab",
    "Lycra Burkha Design",
    "Zoom Fabric Burkha",
    "Shamoo Silk Abaya",
    "Soft Georgette Borka",
    "Premium Fabric Burkha",
    "Breathable Burkha Hijab",
    "Lightweight Burkha",
    "Heavy Fabric Abaya",
    
    # Seasonal
    "Summer Burkha Hijab",
    "Summer Friendly Abaya",
    "Winter Burkha Design",
    "Winter Abaya Coat",
    "All Season Burkha",
    "Lightweight Summer Burkha",
    "Warm Winter Abaya",
    "Monsoon Burkha Hijab",
    
    # Occasions
    "Wedding Burkha Hijab",
    "Bridal Burkha Design",
    "Party Wear Abaya",
    "Eid Burkha Collection",
    "Eid Special Burkha",
    "Ramadan Burkha Hijab",
    "Festive Burkha Design",
    "Ceremonial Abaya Hijab",
    "Nikah Burkha Design",
    "Walima Abaya Hijab",
    "Engagement Burkha",
    "Reception Abaya Design",
    "Formal Event Burkha",
    
    # Special Occasions - Eid
    "Eid Mubarak Burkha",
    "Eid ul Fitr Burkha",
    "Eid ul Adha Abaya",
    "Eid Collection Abaya",
    
    # Special Occasions - Ramadan & Religious
    "Ramadan Collection Burkha",
    "Iftar Burkha Design",
    "Taraweeh Abaya Hijab",
    "Prayer Burkha Hijab",
    "Namaz Burkha Design",
    "Salah Abaya Hijab",
    "Mosque Wear Burkha",
    "Hajj Burkha Hijab",
    "Umrah Abaya Design",
    "Religious Burkha Hijab",
    
    # Fashion Trends & Modern Terms
    "Burkha Design 2026",
    "Latest Burkha Fashion",
    "New Abaya Collection 2026",
    "Trending Burkha Design",
    "Viral Burkha Style",
    "Modern Hijab Fashion",
    "Contemporary Abaya Design",
    "Modest Fashion 2026",
    "New Arrival Burkha",
    "Hijabi Fashion Trends",
    
    # Fit & Size
    "Plus Size Burkha Hijab",
    "Free Size Abaya",
    "Regular Fit Burkha",
    "Loose Fit Abaya",
    "Comfortable Burkha Hijab",
    "Oversized Burkha Design",
    "Slim Fit Burkha",
    "Maternity Burkha Hijab",
    "Nursing Friendly Burkha",
    "Comfort Fit Abaya",
    
    # Length Variations
    "Full Length Burkha",
    "Floor Length Abaya",
    "Ankle Length Burkha",
    "Maxi Burkha Hijab",
    "Long Burkha Design",
    
    # Coverage Types
    "Full Coverage Burkha",
    "Complete Hijab Set",
    "Niqab Style Burkha",
    "Face Veil Burkha",
    "Eye Slit Burkha",
    "Mesh Panel Burkha",
    
    # Age Groups
    "Women Burkha Hijab",
    "Girls Burkha Design",
    "Teen Burkha Style",
    "Young Women Abaya",
    "Mother Daughter Burkha",
    "Matching Burkha Set",
    "Kids Burkha Hijab",
    
    # Sets & Combinations
    "Two Piece Burkha Set",
    "Three Piece Burkha Set",
    "Burkha Niqab Hijab Set",
    "Complete Islamic Dress",
    "Burkha with Undercap",
    "Burkha with Inner Hijab",
    "Abaya with Matching Scarf",
    
    # Hijab Styles & Combinations
    "Burkha with Square Hijab",
    "Abaya with Instant Hijab",
    "Burkha with Jersey Hijab",
    "Matching Hijab Burkha",
    "Contrast Hijab Abaya",
    "Attached Hijab Burkha",
    "Ready to Wear Hijab Set",
    "Khimar Style Hijab",
    
    # Functional Features
    "Easy Wear Burkha",
    "Quick Hijab Burkha",
    "No Pin Hijab Set",
    "Wrinkle Free Burkha",
    "Easy Care Abaya",
    "Machine Washable Burkha",
    "Travel Friendly Abaya",
    "Non See Through Burkha",
    
    # Specific Design Elements
    "Burkha with Pockets",
    "Side Pockets Abaya",
    "Hidden Pockets Burkha",
    "Belted Burkha Design",
    "Tie Waist Abaya",
    "Elastic Cuff Burkha",
    "Hooded Abaya Design",
    "Layered Burkha Style",
    "Pleated Burkha Design",
    "Ruffled Abaya Hijab",
    "Adjustable Burkha",
    
    # Brand & Quality Terms
    "Branded Burkha Hijab",
    "Premium Quality Abaya",
    "High Quality Burkha",
    "Exclusive Burkha Design",
    "Designer Abaya Collection",
    "Boutique Burkha Style",
    "Handcrafted Burkha",
    "Artisan Abaya Design",
    
    # Shopping Related
    "Buy Burkha Hijab Online",
    "Abaya Online Shopping",
    "Affordable Burkha Design",
    "Cheap Burkha Hijab",
    "Budget Abaya Design",
    "Discount Burkha Sale",
    "Best Burkha Collection",
    "Burkha Shopping Online",
    
    # Style Inspiration & Social Media
    "Burkha Outfit Ideas",
    "Abaya Styling Tips",
    "Hijab Fashion Ideas",
    "Modest OOTD Burkha",
    "Burkha Photoshoot",
    "Abaya Fashion Blog",
    "How to Style Burkha",
    "Hijabi Fashion Inspiration",
    "Modest Fashion Blogger",
    
    # Cultural & Traditional
    "Traditional Islamic Dress",
    "Shariah Compliant Burkha",
    "Sunnah Dress Women",
    "Islamic Clothing Women",
    "Muslimah Fashion",
    "Modest Wear Collection",
    "Halal Fashion Burkha",
    "Conservative Dress Style",
    
    # Purpose Specific
    "Daily Wear Burkha",
    "Office Wear Abaya",
    "College Burkha Design",
    "University Abaya Style",
    "Work Appropriate Burkha",
    "Professional Abaya Hijab",
    
    # Combination Searches
    "Black Burkha Nude Hijab",
    "Abaya with Sheila",
    "Gown Style Borka",
    "Simple Office Burkha",
    "Casual Daily Abaya",
    "Elegant Party Burkha",
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

        self.stored_count = 0

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
        self.folder_path = None

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
        safe_name = self.keyword.replace(" ", "_").replace("’", "").replace("'", "")
        self.folder_path = os.path.join(self.output_folder, safe_name)
        os.makedirs(self.folder_path, exist_ok=True)

        query = quote(self.keyword)
        url = f"https://www.pinterest.com/search/pins/?q={query}"

        print("\n" + "=" * 70)
        print(f"🔎 Switching to keyword: {self.keyword}")
        print(f"🌐 Opening: {url}")
        print(f"📁 Saving into: {self.folder_path}")
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
    # Visual highlighting
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

                # save
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

                filename = f"{self.keyword.replace(' ', '_')}_{self.stored_count:05d}_{w}x{h}{ext}"
                filepath = os.path.join(self.folder_path, filename)

                with open(filepath, "wb") as f:
                    f.write(content)

                self.highlight_saved(img, w, h)
                print(f"✅ Saved {self.stored_count}/{self.total_images}: {filename}")
                time.sleep(POLITE_DELAY)

            except Exception:
                self.highlight_skipped(img, "FAILED")
                continue

    # ---------------------------
    # Stagnation detection + keyword switching
    # ---------------------------
    def _update_stagnation(self):
        """
        If seen_urls doesn't increase since last progress tick:
            stagnant_ticks += 1
        else:
            stagnant_ticks = 0
        """
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
    # Main loop
    # ---------------------------
    def run(self):
        try:
            self.setup_driver()

            # start with first keyword
            if not self.keywords:
                print("❌ No keywords provided.")
                return

            self.keyword_index = 0
            self.open_pinterest_for_keyword(self.keywords[self.keyword_index])

            scrolls_done = 0

            while self.stored_count < self.total_images:
                # stop global scrolling safety
                if scrolls_done >= self.max_scrolls:
                    print("⚠️ Reached MAX_SCROLLS safety limit. Stopping.")
                    break

                # process images on current page
                self.process_visible_images()

                if self.stored_count >= self.total_images:
                    break

                # scroll for more
                self.scroll_chunk(times=self.scroll_step)
                scrolls_done += self.scroll_step

                stagnant_ticks = self._update_stagnation()

                print(
                    f"📌 Progress: stored={self.stored_count}/{self.total_images} | "
                    f"seen_urls={len(self.seen_urls)} | scrolls={scrolls_done}/{self.max_scrolls} | "
                    f"keyword='{self.keyword}' | stagnant={stagnant_ticks}/{self.stagnation_limit}"
                )

                # if stuck for N ticks -> switch keyword
                if stagnant_ticks >= self.stagnation_limit:
                    nxt = self._next_keyword()
                    if not nxt:
                        print("⚠️ No more keywords left. Stopping.")
                        break

                    # Switch keyword page, do not reset seen/saved (global uniqueness)
                    self.open_pinterest_for_keyword(nxt)

                    # Optional: do NOT reset scroll counter; but Pinterest is new page,
                    # you may want to keep global safety as is.
                    # scrolls_done remains global.

            print("\n" + "=" * 70)
            print("📊 FINISHED")
            print(f"Stored total:   {self.stored_count}/{self.total_images}")
            print(f"Seen URLs:      {len(self.seen_urls)}")
            print(f"Unique saved:   {len(self.saved_hashes)}")
            print(f"Last keyword:   {self.keyword}")
            print(f"Output base:    {self.output_folder}")
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
    print("🎨 PINTEREST SCRAPER (HI-RES + 2000 + GLOBAL DEDUPE + KEYWORD ROTATION)")
    print("=" * 70)
    print(f"Keywords:       {len(BURKHA_HIJAB_KEYWORDS)}")
    print(f"Output Folder:  {OUTPUT_FOLDER}")
    print(f"Target Images:  {TOTAL_IMAGES}")
    print(f"Min Size:       {MIN_WIDTH}x{MIN_HEIGHT}")
    print(f"Stagnation:     {STAGNATION_LIMIT} ticks without new seen_urls -> switch keyword")
    print(f"Headless:       {HEADLESS}")
    print("=" * 70 + "\n")

    scraper = PinterestScraper(
        keywords=BURKHA_HIJAB_KEYWORDS,
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
