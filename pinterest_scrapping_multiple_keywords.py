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
KEYWORDS = [
    # Basic Men's Terms
    "Men's Jubba",
    "Men's Thobe",
    "Men's Jalabiya",
    "Men's Dishdasha",
    "Men's Kandura",
    "Men's Qamis",
    "Jubba for men",
    "Thobe for men",
    "Men Jalabiya",
    "Male Thobe",
    "Boys Jubba",
    "Mens Islamic Robe",
    
    # Islamic/Arabic General
    "Islamic Men's Clothing",
    "Arabic Thobe Men",
    "Muslim Men's Thobe",
    "Islamic Mens Robe",
    "Muslim Mens Jubba",
    "Arab Men Traditional Dress",
    "Islamic Male Attire",
    "Muslim Men Traditional Clothing",
    
    # Regional Styles - Saudi Arabia
    "Saudi Thobe Men",
    "Saudi Arabian Men's Thobe",
    "Saudi Mens Dishdasha",
    "Saudi Style Thobe Male",
    "Saudi White Thobe Men",
    
    # Regional Styles - UAE/Emirates
    "Emirati Kandura Men",
    "UAE Thobe Men",
    "Emirati Men's Kandura",
    "Dubai Men Kandura",
    "Abu Dhabi Thobe Men",
    
    # Regional Styles - Morocco
    "Moroccan Thobe Men",
    "Moroccan Djellaba Men",
    "Moroccan Men's Jalabiya",
    "Moroccan Gandora Men",
    "Moroccan Male Djellaba",
    
    # Regional Styles - Oman
    "Omani Thobe Men",
    "Omani Dishdasha Men",
    "Omani Men's Traditional Dress",
    
    # Regional Styles - Kuwait
    "Kuwaiti Dishdasha Men",
    "Kuwaiti Thobe Men",
    "Kuwait Men's Traditional Dress",
    
    # Regional Styles - Qatar
    "Qatari Thobe Men",
    "Qatari Dishdasha Men",
    "Qatar Men's Traditional Dress",
    
    # Regional Styles - Egypt/Sudan
    "Sudanese Jalabiya Men",
    "Egyptian Galabeya Men",
    "Sudanese Men's Thobe",
    "Egyptian Men Galabiya",
    
    # Regional Styles - Pakistan/India
    "Pakistani Jubba Men",
    "Indian Jubba Men",
    "Pakistani Men's Kurta",
    "South Asian Men's Thobe",
    
    # Regional Styles - Palestine/Levant
    "Palestinian Thobe Men",
    "Syrian Thobe Men",
    "Levantine Men's Jalabiya",
    
    # Design Features
    "Thobe with Embroidery Men",
    "Embroidered Jubba Men",
    "Designer Thobe Men",
    "Luxury Thobe Men",
    "Premium Jubba Men",
    "Thobe with Collar Men",
    "Collarless Thobe Men",
    "Thobe with Pockets Men",
    "Mandarin Collar Thobe Men",
    "Embroidered Kandura Men",
    
    # Style Categories
    "Modern Thobe Men",
    "Traditional Thobe Men",
    "Casual Thobe Men",
    "Formal Thobe Men",
    "Elegant Jubba Men",
    "Classic Dishdasha Men",
    "Contemporary Thobe Men",
    "Stylish Kandura Men",
    "Trendy Thobe Men",
    "Fashionable Jubba Men",
    
    # Color Variations
    "White Thobe Men",
    "Black Thobe Men",
    "Beige Thobe Men",
    "Grey Thobe Men",
    "Navy Blue Thobe Men",
    "Brown Thobe Men",
    "Cream Thobe Men",
    "Olive Thobe Men",
    "Maroon Jubba Men",
    "Green Thobe Men",
    "Two Tone Thobe Men",
    "Colored Jubba Men",
    "Striped Thobe Men",
    
    # Fabric Types
    "Linen Thobe Men",
    "Cotton Thobe Men",
    "Silk Jubba Men",
    "Polyester Thobe Men",
    "Premium Fabric Thobe Men",
    "Summer Thobe Men",
    "Winter Thobe Men",
    "Lightweight Kandura Men",
    
    # Occasions
    "Wedding Thobe Men",
    "Eid Thobe Men",
    "Ramadan Thobe Men",
    "Prayer Thobe Men",
    "Jummah Thobe Men",
    "Hajj Thobe Men",
    "Umrah Thobe Men",
    "Party Wear Jubba Men",
    "Festive Thobe Men",
    
    # Fashion Trends
    "Thobe Fashion Men 2026",
    "Latest Thobe Design Men",
    "New Jubba Style Men",
    "Trending Thobe Men",
    "Modern Arabic Dress Men",
    "Contemporary Kandura Men",
    
    # Fit & Cut
    "Slim Fit Thobe Men",
    "Regular Fit Jubba Men",
    "Loose Fit Dishdasha Men",
    "Tailored Thobe Men",
    "Custom Fit Kandura Men",
    
    # Length Variations
    "Ankle Length Thobe Men",
    "Short Jubba Men",
    "Long Thobe Men",
    
    # Collar Styles
    "Round Neck Thobe Men",
    "V Neck Jubba Men",
    "Button Collar Thobe Men",
    "Zip Thobe Men",
    
    # Age Groups
    "Adult Men Thobe",
    "Young Men Jubba",
    "Mens Thobe Fashion",
    "Gentleman Thobe",
    "Boys Kandura",
    
    # Additional Specific Terms
    "GCC Thobe Men",
    "Gulf Style Thobe Men",
    "Middle Eastern Men Robe",
    "Arab Traditional Wear Men",
    "Islamic Formal Wear Men",
    "Muslim Prayer Dress Men",
    "Mens Kaftan Arabic",
    "Islamic Tunic Men",
    "Arab Long Dress Men",
    "Muslim Male Traditional Outfit",
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
    print(f"Keywords:       {len(KEYWORDS)}")
    print(f"Output Folder:  {OUTPUT_FOLDER}")
    print(f"Target Images:  {TOTAL_IMAGES}")
    print(f"Min Size:       {MIN_WIDTH}x{MIN_HEIGHT}")
    print(f"Stagnation:     {STAGNATION_LIMIT} ticks without new seen_urls -> switch keyword")
    print(f"Headless:       {HEADLESS}")
    print("=" * 70 + "\n")

    scraper = PinterestScraper(
        keywords=KEYWORDS,
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
