#!/usr/bin/env python3
"""
Pinterest Image Scraper - HI-RES + TARGET COUNT + DEDUPE + VISUAL HIGHLIGHTING (WORKING)

Highlights:
- BLUE  = PROCESSING
- GREEN = SAVED
- RED   = SKIPPED / DUPLICATE / FAILED / TOO SMALL (with label)

Key fixes vs common non-working attempts:
- Never try to pass a JS-returned DOM node as a Selenium element.
- Highlight real Selenium WebElements (img + a chosen ancestor container).
- Force strong visible CSS: outline + boxShadow + zIndex + badge.
- Scroll element into view before applying styles.

Requirements:
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
# CONFIG
# ============================================
SEARCH_KEYWORD = "Jubba for man"
OUTPUT_FOLDER = "data_raw/pinterest_downloads"

TOTAL_IMAGES = 2000

MIN_WIDTH = 1080
MIN_HEIGHT = 720

SCROLL_PAUSE = 3
SCROLL_STEP = 2
MAX_SCROLLS = 5000

HEADLESS = False

REQUEST_TIMEOUT = 25
POLITE_DELAY = 0.15
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

        self.seen_urls = set()
        self.saved_hashes = set()
        self.stored_count = 0

        self.folder_path = os.path.join(
            self.output_folder, self.keyword.replace(" ", "_")
        )

        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Referer": "https://www.pinterest.com/",
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        }

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

    def open_pinterest(self):
        query = quote(self.keyword)
        url = f"https://www.pinterest.com/search/pins/?q={query}"
        print(f"🌐 Opening: {url}")
        self.driver.get(url)

        print("⏳ Waiting for page load...")
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

        print("✅ Page loaded!\n")

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
        # Pinterest loads many images; we grab pinimg images
        try:
            css = 'img[src*="pinimg.com"], img[srcset*="pinimg.com"], img[data-src*="pinimg.com"]'
            return self.driver.find_elements(By.CSS_SELECTOR, css)
        except Exception:
            return []

    # ---------------------------
    # Visual highlighting (WORKING)
    # ---------------------------
    def _scroll_into_view(self, el):
        try:
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block:'center', inline:'center'});", el
            )
        except Exception:
            pass

    def _apply_style(self, el, color, label):
        """
        Apply strong visible outline + badge.
        IMPORTANT: el MUST be a Selenium WebElement.
        """
        try:
            self._scroll_into_view(el)
            self.driver.execute_script(
                """
                const el = arguments[0];
                const color = arguments[1];
                const label = arguments[2];

                // make sure element can show overlays
                el.style.outline = `10px solid ${color}`;
                el.style.outlineOffset = "5px";
                el.style.boxShadow = `0 0 0 4px rgba(255,255,255,0.85), 0 0 0 10px ${color}55`;
                el.style.borderRadius = "15px";
                el.style.position = (getComputedStyle(el).position === "static") ? "relative" : el.style.position;
                el.style.zIndex = "999999";

                // badge
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
                    badge.style.fontSize = "50px";
                    badge.style.fontWeight = "2000";
                    badge.style.letterSpacing = "0.5px";
                    badge.style.color = "#fff";
                    badge.style.boxShadow = "0 2px 10px rgba(0,0,0,0.35)";
                    el.appendChild(badge);
                }
                badge.textContent = label;
                badge.style.background = color;

                // mark so we can find it later
                el.setAttribute("data-gs-state", label);
                """,
                el,
                color,
                label,
            )
        except Exception:
            pass

    def _get_reasonable_container(self, img):
        """
        Return a Selenium WebElement container using XPath (ancestor), not JS-returned nodes.
        We try a few levels up to get a visible card-like box.
        """
        try:
            # Try nearest ancestor divs; pick one that tends to be card-sized.
            # We'll just return the first ancestor div; styling it is usually visible.
            return img.find_element(By.XPATH, "./ancestor::div[1]")
        except Exception:
            return None

    def highlight_processing(self, img):
        # highlight both container and image for visibility
        container = self._get_reasonable_container(img)
        if container:
            self._apply_style(container, "dodgerblue", "PROCESSING")
        self._apply_style(img, "dodgerblue", "PROCESSING")

    def highlight_saved(self, img, w, h):
        container = self._get_reasonable_container(img)
        label = f"SAVED {w}x{h}"
        if container:
            self._apply_style(container, "limegreen", label)
        self._apply_style(img, "limegreen", label)

    def highlight_skipped(self, img, reason):
        container = self._get_reasonable_container(img)
        label = reason
        if container:
            self._apply_style(container, "crimson", label)
        self._apply_style(img, "crimson", label)

    # ---------------------------
    # Image checks + saving
    # ---------------------------
    def _get_dimensions(self, content_bytes):
        try:
            im = Image.open(BytesIO(content_bytes))
            return im.size  # (w, h)
        except Exception:
            return None, None

    def process_visible_images(self):
        os.makedirs(self.folder_path, exist_ok=True)

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

            # BLUE highlight while processing
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

                # Save
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

                # GREEN highlight if saved
                self.highlight_saved(img, w, h)

                print(f"✅ Saved {self.stored_count}/{self.total_images}: {filename}")
                time.sleep(POLITE_DELAY)

            except Exception:
                self.highlight_skipped(img, "FAILED")
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
            print("🚀 Starting scrape loop (VISUAL MODE - WORKING)")
            print(f"Target:         {self.total_images}")
            print(f"Min resolution: {self.min_width}x{self.min_height}")
            print(f"Output:         {self.folder_path}")
            print("=" * 70)

            while self.stored_count < self.total_images and scrolls_done < self.max_scrolls:
                self.process_visible_images()

                if self.stored_count >= self.total_images:
                    break

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
    print("🎨 PINTEREST IMAGE SCRAPER (HI-RES + TARGET + DEDUPE + VISUAL)")
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
    print("Done.\n")


if __name__ == "__main__":
    main()
