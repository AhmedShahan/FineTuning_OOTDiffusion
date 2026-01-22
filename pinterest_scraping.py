#!/usr/bin/env python3
"""
Pinterest Image Scraper - High-Resolution + Target Count + No Duplicates

What this version does:
- Searches Pinterest for a keyword
- Continuously scrolls & discovers new image URLs
- Downloads ONLY images with width >= MIN_WIDTH and height >= MIN_HEIGHT
- Stops after saving TOTAL_IMAGES images
- Never saves the same image twice (URL dedupe + content-hash dedupe)

Requirements:
- selenium
- requests
- pillow

Install:
  pip install selenium requests pillow
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
# EASY CONFIGURATION - JUST EDIT THESE!
# ============================================

SEARCH_KEYWORD = "Jubba for man"
OUTPUT_FOLDER = "data_raw/pinterest_downloads"

TOTAL_IMAGES = 2000

MIN_WIDTH = 1080
MIN_HEIGHT = 720

SCROLL_PAUSE = 3            # seconds between scrolls
SCROLL_STEP = 2             # how many scrolls per loop iteration
MAX_SCROLLS = 5000          # safety limit so it won't loop forever

HEADLESS = False            # True = hidden browser, False = see browser window

REQUEST_TIMEOUT = 25
POLITE_DELAY = 0.15         # small delay between downloads

# ============================================


class PinterestScraper:
    def __init__(
        self,
        keyword,
        output_folder,
        total_images=2000,
        min_width=1080,
        min_height=720,
        scroll_pause=3,
        scroll_step=2,
        max_scrolls=5000,
        headless=False,
    ):
        self.keyword = keyword
        self.output_folder = output_folder

        self.total_images = total_images
        self.min_width = min_width
        self.min_height = min_height

        self.scroll_pause = scroll_pause
        self.scroll_step = scroll_step
        self.max_scrolls = max_scrolls
        self.headless = headless

        self.driver = None

        # Dedupe controls
        self.seen_urls = set()       # URLs we already attempted
        self.saved_hashes = set()    # content-hash of saved images (strong dedupe)

        self.stored_count = 0

        # Output folder per keyword
        self.folder_path = os.path.join(
            self.output_folder, self.keyword.replace(" ", "_")
        )

    # ---------------------------
    # Browser setup / navigation
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

        # Stealth-ish tweaks (not guaranteed vs Pinterest)
        try:
            self.driver.execute_cdp_cmd("Network.setUserAgentOverride", {
                "userAgent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
            })
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
        except Exception:
            pass

        print("✅ WebDriver ready!\n")

    def open_pinterest(self):
        query = quote(self.keyword)
        search_url = f"https://www.pinterest.com/search/pins/?q={query}"

        print(f"🌐 Opening: {search_url}")
        self.driver.get(search_url)

        print("⏳ Waiting for page load...")
        time.sleep(5)

        # Close popups if any
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

        print("✅ Page loaded!\n")

    # ---------------------------
    # Scrolling / extraction
    # ---------------------------
    def scroll_chunk(self, times=2):
        """Scroll a few times to load more content"""
        for _ in range(times):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(self.scroll_pause)

    def extract_images(self):
        """
        Extract pinimg.com URLs from:
        - img[src]
        - img[data-src]
        - img[srcset]
        - page source regex fallback
        """
        urls = set()

        # Method 1: direct img tags
        try:
            imgs = self.driver.find_elements(By.TAG_NAME, "img")
            for img in imgs:
                # src
                src = img.get_attribute("src")
                if src and "pinimg.com" in src:
                    urls.add(self._normalize_and_upgrade_url(src))

                # data-src
                data_src = img.get_attribute("data-src")
                if data_src and "pinimg.com" in data_src:
                    urls.add(self._normalize_and_upgrade_url(data_src))

                # srcset (take last = largest candidate)
                srcset = img.get_attribute("srcset")
                if srcset and "pinimg.com" in srcset:
                    found = re.findall(r"(https://[^\s,]+)", srcset)
                    if found:
                        urls.add(self._normalize_and_upgrade_url(found[-1]))
        except Exception:
            pass

        # Method 2: regex fallback on full HTML
        try:
            page_source = self.driver.page_source
            pinimg_urls = re.findall(r"https://i\.pinimg\.com/[^\"'>\s]+", page_source)
            for u in pinimg_urls:
                urls.add(self._normalize_and_upgrade_url(u))
        except Exception:
            pass

        return list(urls)

    def _normalize_and_upgrade_url(self, url: str) -> str:
        """Clean URL and upgrade known Pinterest sizes to originals when possible."""
        if not url:
            return url

        url = url.split("?")[0].strip()

        # Pinterest often uses: /236x/ /474x/ /564x/ /736x/ -> try /originals/
        for size in ("/236x/", "/474x/", "/564x/", "/736x/"):
            if size in url:
                url = url.replace(size, "/originals/")
                break

        return url

    # ---------------------------
    # Download + resolution filter
    # ---------------------------
    def _get_dimensions(self, content_bytes):
        """Return (width, height) or (None, None)."""
        try:
            im = Image.open(BytesIO(content_bytes))
            return im.size  # (w, h)
        except Exception:
            return None, None

    def download_candidate_urls(self, candidate_urls):
        """Try downloading candidate URLs and save those meeting resolution constraints."""
        os.makedirs(self.folder_path, exist_ok=True)

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Referer": "https://www.pinterest.com/",
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        }

        for url in candidate_urls:
            if self.stored_count >= self.total_images:
                return

            # URL dedupe
            if url in self.seen_urls:
                continue
            self.seen_urls.add(url)

            try:
                r = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
                r.raise_for_status()

                content = r.content
                if not content or len(content) < 1024:  # ignore tiny responses
                    continue

                # Strong dedupe by content hash (prevents same image via different URLs)
                content_hash = hashlib.md5(content).hexdigest()
                if content_hash in self.saved_hashes:
                    continue

                w, h = self._get_dimensions(content)
                if not w or not h:
                    continue

                # Resolution filter
                if w < self.min_width or h < self.min_height:
                    continue

                # Passed -> save
                self.saved_hashes.add(content_hash)
                self.stored_count += 1

                # Determine extension
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

                print(f"✅ Saved {self.stored_count}/{self.total_images}: {filename}")

                time.sleep(POLITE_DELAY)

            except Exception:
                # Skip failures silently (uncomment for debugging)
                # print(f"❌ Failed: {url} | {str(e)[:80]}")
                continue

    # ---------------------------
    # Main loop
    # ---------------------------
    def run(self):
        try:
            self.setup_driver()
            self.open_pinterest()

            scrolls_done = 0

            print("=" * 70)
            print("🚀 Starting scrape loop")
            print(f"Target: {self.total_images} images")
            print(f"Min resolution: {self.min_width}x{self.min_height}")
            print(f"Output: {self.folder_path}")
            print("=" * 70)

            while self.stored_count < self.total_images and scrolls_done < self.max_scrolls:
                candidate_urls = self.extract_images()
                if candidate_urls:
                    self.download_candidate_urls(candidate_urls)

                if self.stored_count >= self.total_images:
                    break

                # Scroll for newer images
                self.scroll_chunk(times=self.scroll_step)
                scrolls_done += self.scroll_step

                print(
                    f"📌 Progress: stored={self.stored_count}/{self.total_images} | "
                    f"seen_urls={len(self.seen_urls)} | scrolls={scrolls_done}/{self.max_scrolls}"
                )

            print("\n" + "=" * 70)
            print("📊 FINISHED")
            print(f"Keyword:        {self.keyword}")
            print(f"Stored:         {self.stored_count}/{self.total_images}")
            print(f"Seen URLs:      {len(self.seen_urls)}")
            print(f"Unique saved:   {len(self.saved_hashes)}")
            print(f"Scrolls used:   {scrolls_done}/{self.max_scrolls}")
            print(f"Location:       {self.folder_path}")
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
    print("🎨 PINTEREST IMAGE SCRAPER (HI-RES + 2000 TARGET + DEDUPE)")
    print("=" * 70)
    print(f"Keyword:        {SEARCH_KEYWORD}")
    print(f"Output Folder:  {OUTPUT_FOLDER}")
    print(f"Target Images:  {TOTAL_IMAGES}")
    print(f"Min Size:       {MIN_WIDTH}x{MIN_HEIGHT}")
    print(f"Scroll Pause:   {SCROLL_PAUSE}s")
    print(f"Scroll Step:    {SCROLL_STEP}")
    print(f"Headless:       {HEADLESS}")
    print("=" * 70 + "\n")

    scraper = PinterestScraper(
        keyword=SEARCH_KEYWORD,
        output_folder=OUTPUT_FOLDER,
        total_images=TOTAL_IMAGES,
        min_width=MIN_WIDTH,
        min_height=MIN_HEIGHT,
        scroll_pause=SCROLL_PAUSE,
        scroll_step=SCROLL_STEP,
        max_scrolls=MAX_SCROLLS,
        headless=HEADLESS,
    )
    scraper.run()

    print("✨ Done!\n")


if __name__ == "__main__":
    main()
