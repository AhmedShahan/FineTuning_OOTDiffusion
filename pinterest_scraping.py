#!/usr/bin/env python3
"""
Pinterest Image Scraper - Enhanced Version with Better Detection
Handles Pinterest's dynamic content loading
"""

import os
import time
import json
import requests
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

# ============================================
# EASY CONFIGURATION - JUST EDIT THESE!
# ============================================

SEARCH_KEYWORD = "Jubba for man"                 # What to search for
OUTPUT_FOLDER = "data_raw/pinterest_downloads"      # Folder to save images
NUM_SCROLLS = 10                           # How many times to scroll (more = more images)
SCROLL_PAUSE = 3                           # Seconds between scrolls
HEADLESS = False                           # True = hidden browser, False = see browser window

# ============================================

class PinterestScraper:
    def __init__(self, keyword, output_folder, num_scrolls=10, scroll_pause=3, headless=False):
        self.keyword = keyword
        self.output_folder = output_folder
        self.num_scrolls = num_scrolls
        self.scroll_pause = scroll_pause
        self.headless = headless
        self.driver = None
        self.image_urls = set()
        
    def setup_driver(self):
        """Initialize Chrome WebDriver"""
        print("⚙️  Setting up Chrome WebDriver...")
        
        options = Options()
        
        if self.headless:
            options.add_argument('--headless')
        
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_experimental_option("prefs", {
            "profile.default_content_setting_values.notifications": 2,
            "profile.default_content_settings.popups": 0,
        })
        
        self.driver = webdriver.Chrome(options=options)
        
        # Stealth mode
        self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        print("✅ WebDriver ready!\n")
        
    def open_pinterest(self):
        """Open Pinterest search page"""
        search_url = f"https://www.pinterest.com/search/pins/?q={self.keyword.replace(' ', '%20')}"
        
        print(f"🌐 Opening: {search_url}")
        self.driver.get(search_url)
        
        print(f"⏳ Waiting for page load...")
        time.sleep(5)
        
        # Handle any popups
        try:
            # Try to close any modals
            close_buttons = self.driver.find_elements(By.CSS_SELECTOR, '[aria-label="Close"]')
            for btn in close_buttons:
                try:
                    btn.click()
                    time.sleep(0.5)
                except:
                    pass
        except:
            pass
        
        print("✅ Page loaded!\n")
        
    def scroll_and_load(self):
        """Scroll page to load more images"""
        print(f"📜 Scrolling page {self.num_scrolls} times...\n")
        
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        
        for i in range(self.num_scrolls):
            # Scroll down
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            print(f"   Scroll {i+1}/{self.num_scrolls} - Waiting {self.scroll_pause}s for content to load...")
            time.sleep(self.scroll_pause)
            
            # Check if we've reached the bottom
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            
            if new_height == last_height:
                print(f"   ℹ️  No more content loading (reached bottom at scroll {i+1})")
                break
                
            last_height = new_height
        
        # One final scroll to top to ensure all images are in viewport
        self.driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)
        
        print("\n✅ Scrolling complete!\n")
        
    def extract_images(self):
        """Extract all image URLs from page"""
        print("🔍 Extracting image URLs from page...\n")
        
        # Multiple methods to find images
        methods = [
            ('CSS: img[src*="pinimg.com"]', By.CSS_SELECTOR, 'img[src*="pinimg.com"]'),
            ('CSS: img[srcset*="pinimg.com"]', By.CSS_SELECTOR, 'img[srcset*="pinimg.com"]'),
            ('CSS: img', By.CSS_SELECTOR, 'img'),
            ('TAG: img', By.TAG_NAME, 'img'),
        ]
        
        for method_name, by_type, selector in methods:
            try:
                elements = self.driver.find_elements(by_type, selector)
                print(f"   {method_name}: Found {len(elements)} elements")
                
                for element in elements:
                    self._extract_url_from_element(element)
                    
            except Exception as e:
                print(f"   ⚠️  {method_name} failed: {str(e)[:50]}")
        
        # Also check page source for any missed URLs
        page_source = self.driver.page_source
        pinimg_urls = re.findall(r'https://i\.pinimg\.com/[^"\'>\s]+', page_source)
        
        for url in pinimg_urls:
            if url not in self.image_urls:
                self.image_urls.add(self._upgrade_url_quality(url))
        
        print(f"\n✅ Total unique images found: {len(self.image_urls)}\n")
        
        return list(self.image_urls)
    
    def _extract_url_from_element(self, element):
        """Extract URL from an image element"""
        try:
            # Try different attributes
            url = None
            
            # Try src
            src = element.get_attribute('src')
            if src and 'pinimg.com' in src:
                url = src
            
            # Try data-src
            if not url:
                data_src = element.get_attribute('data-src')
                if data_src and 'pinimg.com' in data_src:
                    url = data_src
            
            # Try srcset
            if not url:
                srcset = element.get_attribute('srcset')
                if srcset and 'pinimg.com' in srcset:
                    # Parse srcset (format: "url 1x, url 2x")
                    urls = re.findall(r'(https://[^\s,]+)', srcset)
                    if urls:
                        url = urls[-1]  # Get highest resolution
            
            if url:
                # Clean and upgrade URL
                url = url.split('?')[0]  # Remove query parameters
                url = self._upgrade_url_quality(url)
                self.image_urls.add(url)
                
        except Exception as e:
            pass
    
    def _upgrade_url_quality(self, url):
        """Convert image URL to highest quality version"""
        # Pinterest image URL structure: https://i.pinimg.com/{size}/...
        # Sizes: 236x, 474x, 564x, 736x, originals
        
        replacements = ['/236x/', '/474x/', '/564x/', '/736x/']
        
        for size in replacements:
            if size in url:
                return url.replace(size, '/originals/')
        
        return url
    
    def download_images(self, image_urls):
        """Download all images to folder"""
        # Create folder
        folder_path = os.path.join(self.output_folder, self.keyword.replace(' ', '_'))
        os.makedirs(folder_path, exist_ok=True)
        
        print(f"💾 Downloading {len(image_urls)} images to: {folder_path}\n")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.pinterest.com/',
            'Accept': 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8'
        }
        
        success_count = 0
        fail_count = 0
        
        for idx, url in enumerate(image_urls, 1):
            try:
                # Get file extension
                ext = '.jpg'
                if '.png' in url.lower():
                    ext = '.png'
                elif '.gif' in url.lower():
                    ext = '.gif'
                elif '.webp' in url.lower():
                    ext = '.webp'
                
                filename = f"{self.keyword.replace(' ', '_')}_{idx:04d}{ext}"
                filepath = os.path.join(folder_path, filename)
                
                # Skip if already exists
                if os.path.exists(filepath):
                    print(f"   [{idx}/{len(image_urls)}] ⏭️  {filename} (already exists)")
                    success_count += 1
                    continue
                
                # Download
                response = requests.get(url, headers=headers, timeout=15)
                response.raise_for_status()
                
                # Save
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                
                file_size = len(response.content) / 1024
                success_count += 1
                print(f"   [{idx}/{len(image_urls)}] ✅ {filename} ({file_size:.1f} KB)")
                
                time.sleep(0.2)  # Polite delay
                
            except Exception as e:
                fail_count += 1
                print(f"   [{idx}/{len(image_urls)}] ❌ Failed: {str(e)[:60]}")
        
        # Summary
        print("\n" + "="*70)
        print("📊 DOWNLOAD COMPLETE!")
        print("="*70)
        print(f"  Keyword:        {self.keyword}")
        print(f"  Total Found:    {len(image_urls)}")
        print(f"  ✅ Success:     {success_count}")
        print(f"  ❌ Failed:      {fail_count}")
        print(f"  📁 Location:    {folder_path}")
        print("="*70 + "\n")
        
    def run(self):
        """Main execution flow"""
        try:
            self.setup_driver()
            self.open_pinterest()
            self.scroll_and_load()
            image_urls = self.extract_images()
            
            if self.driver:
                self.driver.quit()
                print("🔒 Browser closed\n")
            
            if image_urls:
                self.download_images(image_urls)
            else:
                print("⚠️  No images found!")
                print("   Possible issues:")
                print("   - Pinterest blocked the request")
                print("   - Try with HEADLESS = False to see the browser")
                print("   - Check your internet connection")
                
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted by user!")
            
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()
            
        finally:
            if self.driver:
                self.driver.quit()

def main():
    """Entry point"""
    print("\n" + "="*70)
    print("🎨 PINTEREST IMAGE SCRAPER")
    print("="*70)
    print(f"  Keyword:        {SEARCH_KEYWORD}")
    print(f"  Output Folder:  {OUTPUT_FOLDER}")
    print(f"  Scrolls:        {NUM_SCROLLS}")
    print(f"  Scroll Pause:   {SCROLL_PAUSE}s")
    print(f"  Headless:       {HEADLESS}")
    print("="*70 + "\n")
    
    scraper = PinterestScraper(
        keyword=SEARCH_KEYWORD,
        output_folder=OUTPUT_FOLDER,
        num_scrolls=NUM_SCROLLS,
        scroll_pause=SCROLL_PAUSE,
        headless=HEADLESS
    )
    
    scraper.run()
    
    print("✨ Done!\n")

if __name__ == "__main__":
    main()
