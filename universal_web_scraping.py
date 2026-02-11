#!/usr/bin/env python3
"""
DYNAMIC WEBSITE CRAWLER FOR JUBBA/THOBE SCRAPING
ধাপ ১: পুরো ওয়েবসাইট থেকে সব লিংক বের করা (Crawl all links)
ধাপ ২: LLM দিয়ে Jubba/Thobe related লিংক ফিল্টার করা
ধাপ ৩: সেই লিংকগুলো থেকে ছবি স্ক্র্যাপ করা + Vision API দিয়ে verify
"""

import os
import asyncio
import aiohttp
import json
import base64
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Set

from dotenv import load_dotenv
from playwright.async_api import async_playwright
from groq import Groq
from collections import deque

load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY")
if not API_KEY:
    raise ValueError("GROQ_API_KEY not found in .env file")

groq_client = Groq(api_key=API_KEY)

# আপনার ওয়েবসাইট এখানে দিন
WEBSITES_TO_CRAWL = [
    "https://mashroostore.com",
    # আরও ওয়েবসাইট যোগ করুন
]

class DynamicWebCrawler:
    """
    পুরো ওয়েবসাইট crawl করে সব লিংক বের করে, তারপর LLM দিয়ে ফিল্টার করে স্ক্র্যাপ করে
    """
    
    def __init__(self, 
                 output_dir="dynamic_jubba_scraper",
                 max_pages_to_crawl=500,  # প্রতি সাইটে সর্বোচ্চ কত পেজ crawl করবে
                 max_depth=3,  # কত লেভেল পর্যন্ত যাবে
                 text_model="llama-3.3-70b-versatile",
                 vision_model="llama-3.2-90b-vision-preview"):
        
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.max_pages_to_crawl = max_pages_to_crawl
        self.max_depth = max_depth
        self.text_model = text_model
        self.vision_model = vision_model
        self.session = None
        
        self.stats = {
            'start_time': datetime.now().isoformat(),
            'sites_processed': 0,
            'total_links_discovered': 0,
            'total_links_filtered_by_llm': 0,
            'total_images_checked': 0,
            'total_images_downloaded': 0,
            'sites_details': {}
        }

    async def create_session(self):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(headers=headers, timeout=timeout)

    async def close_session(self):
        if self.session:
            await self.session.close()

    def is_same_domain(self, url: str, base_url: str) -> bool:
        """চেক করে দুটি URL একই ডোমেইনের কিনা"""
        return urlparse(url).netloc == urlparse(base_url).netloc

    def clean_url(self, url: str) -> str:
        """URL থেকে fragment (#) বাদ দেয়"""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

    async def crawl_website_links(self, browser, base_url: str) -> List[Dict]:
        """
        ধাপ ১: পুরো ওয়েবসাইট crawl করে সব লিংক বের করা
        BFS (Breadth-First Search) algorithm ব্যবহার করে
        """
        print(f"\n{'='*80}")
        print(f"🕷️  CRAWLING WEBSITE: {base_url}")
        print(f"{'='*80}")
        
        discovered_links = []  # সব লিংক এখানে জমা হবে
        visited_urls = set()  # যে URLগুলো visit করা হয়েছে
        queue = deque([(base_url, 0)])  # (URL, depth) queue
        
        context = await browser.new_context()
        
        while queue and len(visited_urls) < self.max_pages_to_crawl:
            current_url, depth = queue.popleft()
            
            # Depth limit check
            if depth > self.max_depth:
                continue
            
            # Already visited check
            clean_current = self.clean_url(current_url)
            if clean_current in visited_urls:
                continue
            
            # Same domain check
            if not self.is_same_domain(current_url, base_url):
                continue
            
            try:
                print(f"📄 [{len(visited_urls)+1}/{self.max_pages_to_crawl}] Depth {depth}: {current_url[:80]}...")
                
                page = await context.new_page()
                await page.goto(current_url, timeout=20000, wait_until='domcontentloaded')
                await asyncio.sleep(1)
                
                # এই পেজ থেকে সব লিংক বের করা
                links_data = await page.evaluate('''() => {
                    const links = Array.from(document.querySelectorAll('a[href]'));
                    return links.map(a => ({
                        href: a.href,
                        text: (a.textContent || '').trim().substring(0, 100),
                        title: a.title || '',
                        class: a.className || ''
                    })).filter(link => 
                        link.href && 
                        !link.href.includes('javascript:') &&
                        !link.href.includes('mailto:') &&
                        !link.href.includes('tel:')
                    );
                }''')
                
                # লিংকগুলো process করা
                for link_data in links_data:
                    full_url = urljoin(current_url, link_data['href'])
                    clean_full = self.clean_url(full_url)
                    
                    # Same domain এবং not visited
                    if self.is_same_domain(full_url, base_url) and clean_full not in visited_urls:
                        # লিংক save করা
                        discovered_links.append({
                            'url': clean_full,
                            'text': link_data['text'],
                            'title': link_data['title'],
                            'found_on': current_url,
                            'depth': depth + 1
                        })
                        
                        # Queue তে add করা (পরে visit করার জন্য)
                        if depth + 1 <= self.max_depth:
                            queue.append((clean_full, depth + 1))
                
                visited_urls.add(clean_current)
                await page.close()
                
                # Rate limiting
                await asyncio.sleep(0.5)
                
            except Exception as e:
                print(f"  ⚠️ Error crawling {current_url[:50]}: {str(e)[:50]}")
                continue
        
        await context.close()
        
        # Deduplicate links
        unique_links = {}
        for link in discovered_links:
            if link['url'] not in unique_links:
                unique_links[link['url']] = link
        
        final_links = list(unique_links.values())
        
        print(f"\n✅ Crawling complete!")
        print(f"   Total pages visited: {len(visited_urls)}")
        print(f"   Total unique links discovered: {len(final_links)}")
        
        self.stats['total_links_discovered'] += len(final_links)
        
        return final_links

    async def filter_links_with_llm(self, all_links: List[Dict], base_url: str) -> List[str]:
        """
        ধাপ ২: LLM দিয়ে Jubba/Thobe related লিংক ফিল্টার করা
        """
        print(f"\n{'='*80}")
        print(f"🤖 LLM FILTERING LINKS")
        print(f"{'='*80}")
        print(f"Total links to analyze: {len(all_links)}")
        
        # LLM এর জন্য links prepare করা
        links_for_llm = []
        for link in all_links[:500]:  # Max 500 links to avoid context limit
            links_for_llm.append({
                'url': link['url'],
                'text': link['text'],
                'title': link['title']
            })
        
        prompt = f"""
তুমি একটি e-commerce ওয়েবসাইট analyze করছো: {base_url}

আমি তোমাকে এই ওয়েবসাইটের সব লিংক দিয়েছি। তোমার কাজ হলো শুধুমাত্র সেই লিংকগুলো select করা যেগুলোতে **Men's Traditional Islamic Clothing** (Thobes, Jubbas, Dishdashas) পাওয়া যাবে।

TARGET PRODUCTS:
- Men's Thobes (ثوب رجالي)
- Men's Jubbas (জলবিয়া / جلابية رجالي)
- Men's Dishdashas (دشداشة)
- Men's Kanduras
- Men's Islamic Robes
- Traditional Arabic Men's Clothing

AVAILABLE LINKS:
{json.dumps(links_for_llm, indent=2, ensure_ascii=False)}

TASK:
উপরের লিংকগুলো analysis করে যেগুলোতে আমাদের target products থাকার সম্ভাবনা আছে সেগুলোর URL return করো।

PRIORITIZE:
1. Category/collection pages (যেখানে অনেকগুলো product দেখায়)
2. Men's clothing sections
3. Islamic/Traditional/Modest clothing categories
4. Product listing pages

AVOID:
- Women's/Kids clothing
- Individual product pages (আমরা category pages চাই)
- Non-clothing items
- Account/Cart/Checkout pages

Response ONLY JSON format এ:
{{
  "relevant_urls": ["url1", "url2", "url3", ...],
  "reasoning": "Brief explanation"
}}

Maximum 50 URLs return করো।
"""

        try:
            print(f"  🤖 Sending {len(links_for_llm)} links to LLM for analysis...")
            
            response = await asyncio.to_thread(
                groq_client.chat.completions.create,
                model=self.text_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at analyzing e-commerce websites. Always respond with valid JSON only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=3000
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Parse JSON
            if '```json' in response_text:
                json_part = response_text.split('```json')[1].split('```')[0]
            elif '```' in response_text:
                json_part = response_text.split('```')[1].split('```')[0]
            else:
                json_part = response_text
            
            result = json.loads(json_part)
            relevant_urls = result.get('relevant_urls', [])
            
            print(f"\n✅ LLM Filtering Complete!")
            print(f"   Relevant URLs found: {len(relevant_urls)}")
            print(f"   Reasoning: {result.get('reasoning', 'N/A')}")
            
            # Print top 10 URLs
            print(f"\n   Top relevant URLs:")
            for i, url in enumerate(relevant_urls[:10], 1):
                print(f"   {i}. {url}")
            
            self.stats['total_links_filtered_by_llm'] += len(relevant_urls)
            
            return relevant_urls
            
        except Exception as e:
            print(f"  ❌ LLM filtering failed: {str(e)}")
            print(f"  Using fallback keyword filtering...")
            
            # Fallback: keyword-based filtering
            relevant = []
            keywords = ['thobe', 'jubba', 'dishdasha', 'kandura', 'islamic', 'traditional', 'men', 'male']
            for link in all_links:
                url_lower = link['url'].lower()
                text_lower = link['text'].lower()
                if any(kw in url_lower or kw in text_lower for kw in keywords):
                    if 'women' not in url_lower and 'kids' not in url_lower:
                        relevant.append(link['url'])
            
            return relevant[:50]

    async def verify_image_with_vision(self, image_url: str) -> Dict:
        """Vision API দিয়ে image verify করা"""
        try:
            async with self.session.get(image_url, timeout=15) as resp:
                if resp.status != 200:
                    return {'is_relevant': False, 'reason': 'download_failed'}
                
                image_data = await resp.read()
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                content_type = resp.headers.get('content-type', 'image/jpeg')
            
            vision_prompt = """
Is this a MEN'S TRADITIONAL ISLAMIC GARMENT (thobe/jubba/dishdasha)?

ACCEPT: Men's Thobe, Jubba, Dishdasha, Kandura, Islamic Robe
REJECT: Women's/kids clothing, western wear, accessories only, non-clothing

Respond ONLY JSON:
{"is_jubba_thobe": true/false, "confidence": "high/medium/low", "reason": "brief explanation"}
"""
            
            response = await asyncio.to_thread(
                groq_client.chat.completions.create,
                model=self.vision_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": vision_prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:{content_type};base64,{image_base64}"}
                            }
                        ]
                    }
                ],
                temperature=0.2,
                max_tokens=200
            )
            
            vision_result = response.choices[0].message.content.strip()
            
            if '```json' in vision_result:
                json_part = vision_result.split('```json')[1].split('```')[0]
            elif '```' in vision_result:
                json_part = vision_result.split('```')[1].split('```')[0]
            else:
                json_part = vision_result
            
            result = json.loads(json_part)
            
            if result.get('is_jubba_thobe', False):
                return {
                    'is_relevant': True,
                    'confidence': result.get('confidence', 'unknown'),
                    'reason': result.get('reason', ''),
                    'image_data': image_data
                }
            else:
                return {'is_relevant': False, 'reason': result.get('reason', '')}
                
        except Exception as e:
            return {'is_relevant': False, 'reason': f'error: {str(e)[:50]}'}

    async def scrape_page_images(self, browser, page_url: str, page_index: int, domain: str) -> int:
        """
        ধাপ ৩: একটি page থেকে images scrape করা
        """
        print(f"\n  🔗 [{page_index}] {page_url}")
        
        try:
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto(page_url, timeout=30000, wait_until='domcontentloaded')
            
            # Scroll
            await page.evaluate("""
                async () => {
                    for(let i=0; i<3; i++) {
                        window.scrollBy(0, window.innerHeight);
                        await new Promise(r => setTimeout(r, 500));
                    }
                }
            """)
            await asyncio.sleep(2)
            
            # Extract images
            image_urls = await page.evaluate('''() => {
                return Array.from(document.images)
                    .filter(img => img.complete && img.naturalWidth >= 200 && img.naturalHeight >= 200)
                    .map(img => img.currentSrc || img.src)
                    .filter(src => {
                        const s = src.toLowerCase();
                        return !s.includes('logo') && !s.includes('icon') && !s.includes('banner');
                    });
            }''')
            
            # Convert to absolute
            absolute_urls = []
            for img_url in image_urls:
                full_url = urljoin(page_url, img_url)
                if full_url.startswith('http'):
                    absolute_urls.append(full_url)
            
            await page.close()
            await context.close()
            
            if not absolute_urls:
                print(f"    ⚠️ No images found")
                return 0
            
            print(f"    🖼️  Found {len(absolute_urls)} images, verifying...")
            
            # Save path
            save_path = self.output_dir / domain
            save_path.mkdir(parents=True, exist_ok=True)
            
            # Verify images
            downloaded = 0
            for i, img_url in enumerate(absolute_urls[:30], 1):  # Max 30 per page
                self.stats['total_images_checked'] += 1
                
                verification = await self.verify_image_with_vision(img_url)
                
                if verification.get('is_relevant'):
                    ext = Path(urlparse(img_url).path).suffix or '.jpg'
                    filename = f"page{page_index}_img{i}{ext}"
                    
                    with open(save_path / filename, 'wb') as f:
                        f.write(verification['image_data'])
                    
                    downloaded += 1
                    self.stats['total_images_downloaded'] += 1
                    print(f"    ✅ [{i}] Saved: {filename}")
                
                await asyncio.sleep(0.3)  # Rate limit
            
            print(f"    💾 Downloaded: {downloaded}/{len(absolute_urls[:30])}")
            return downloaded
            
        except Exception as e:
            print(f"    ❌ Error: {str(e)[:80]}")
            return 0

    async def process_website(self, browser, website_url: str):
        """একটি সম্পূর্ণ ওয়েবসাইট process করা"""
        domain = urlparse(website_url).netloc.replace('www.', '').replace('.', '_')
        
        site_stats = {
            'url': website_url,
            'links_discovered': 0,
            'relevant_links': 0,
            'images_downloaded': 0
        }
        
        print(f"\n{'#'*80}")
        print(f"🌐 PROCESSING WEBSITE: {website_url}")
        print(f"{'#'*80}")
        
        # ধাপ ১: সব লিংক বের করা
        all_links = await self.crawl_website_links(browser, website_url)
        site_stats['links_discovered'] = len(all_links)
        
        if not all_links:
            print(f"❌ No links discovered, skipping...")
            return site_stats
        
        # ধাপ ২: LLM দিয়ে filter করা
        relevant_urls = await self.filter_links_with_llm(all_links, website_url)
        site_stats['relevant_links'] = len(relevant_urls)
        
        if not relevant_urls:
            print(f"❌ No relevant links found by LLM, skipping...")
            return site_stats
        
        # ধাপ ৩: প্রতিটি relevant page থেকে images scrape করা
        print(f"\n{'='*80}")
        print(f"📸 SCRAPING IMAGES FROM {len(relevant_urls)} PAGES")
        print(f"{'='*80}")
        
        total_downloaded = 0
        for i, url in enumerate(relevant_urls[:25], 1):  # Max 25 pages
            downloaded = await self.scrape_page_images(browser, url, i, domain)
            total_downloaded += downloaded
        
        site_stats['images_downloaded'] = total_downloaded
        
        print(f"\n✅ Website complete: {total_downloaded} images downloaded")
        
        self.stats['sites_details'][website_url] = site_stats
        self.stats['sites_processed'] += 1
        
        return site_stats

    async def run(self):
        """Main function"""
        print(f"\n{'#'*80}")
        print(f"🚀 DYNAMIC JUBBA/THOBE WEB CRAWLER")
        print(f"{'#'*80}")
        print(f"🌐 Websites to crawl: {len(WEBSITES_TO_CRAWL)}")
        print(f"📊 Max pages per site: {self.max_pages_to_crawl}")
        print(f"📏 Max depth: {self.max_depth}")
        print(f"🤖 Text Model: {self.text_model}")
        print(f"👁️  Vision Model: {self.vision_model}")
        print(f"{'#'*80}\n")
        
        await self.create_session()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            
            for website in WEBSITES_TO_CRAWL:
                await self.process_website(browser, website)
            
            await browser.close()
        
        await self.close_session()
        
        # Save final report
        self.stats['end_time'] = datetime.now().isoformat()
        report_file = self.output_dir / f"crawl_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, indent=2, ensure_ascii=False)
        
        # Print summary
        print(f"\n{'#'*80}")
        print(f"📊 FINAL SUMMARY")
        print(f"{'#'*80}")
        print(f"✅ Websites processed: {self.stats['sites_processed']}")
        print(f"🔗 Total links discovered: {self.stats['total_links_discovered']}")
        print(f"🎯 Relevant links (by LLM): {self.stats['total_links_filtered_by_llm']}")
        print(f"🔍 Images checked: {self.stats['total_images_checked']}")
        print(f"✅ Images downloaded: {self.stats['total_images_downloaded']}")
        print(f"📁 Output: {self.output_dir.absolute()}")
        print(f"📄 Report: {report_file}")
        print(f"{'#'*80}\n")


async def main():
    crawler = DynamicWebCrawler(
        output_dir="dynamic_jubba_scraper",
        max_pages_to_crawl=500,  # প্রতি সাইটে সর্বোচ্চ ৫০০ পেজ
        max_depth=3,  # ৩ লেভেল গভীর যাবে
        text_model="llama-3.3-70b-versatile",
        vision_model="llama-3.2-90b-vision-preview"
    )
    await crawler.run()


if __name__ == "__main__":
    asyncio.run(main())