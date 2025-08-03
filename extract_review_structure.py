#!/usr/bin/env python3
"""
Extract the actual review structure from Shopify App Store
"""

import asyncio
import logging
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def extract_review_structure():
    """Extract the actual structure of review elements"""
    
    test_url = "https://apps.shopify.com/klaviyo-email-marketing/reviews"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            await page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            logger.info(f"Loading: {test_url}")
            await page.goto(test_url, wait_until='networkidle', timeout=30000)
            
            # Wait for content to load
            await page.wait_for_timeout(5000)
            
            # Let's examine the page content more carefully
            logger.info("Extracting full page structure...")
            
            # Get the main content and look for review-like structures
            review_content = await page.evaluate("""
                () => {
                    // Find text content that looks like reviews
                    const walker = document.createTreeWalker(
                        document.body,
                        NodeFilter.SHOW_TEXT,
                        {
                            acceptNode: function(node) {
                                const text = node.textContent.trim();
                                // Look for text that might be reviews (contains common review phrases)
                                if (text.length > 20 && (
                                    text.includes('ago') ||
                                    text.includes('star') ||
                                    text.includes('recommend') ||
                                    text.includes('great') ||
                                    text.includes('good') ||
                                    text.includes('love') ||
                                    text.includes('app') ||
                                    text.includes('customer') ||
                                    text.includes('support')
                                )) {
                                    return NodeFilter.FILTER_ACCEPT;
                                }
                                return NodeFilter.FILTER_REJECT;
                            }
                        }
                    );
                    
                    const reviewTexts = [];
                    let node;
                    while (node = walker.nextNode()) {
                        const parent = node.parentElement;
                        if (parent) {
                            reviewTexts.push({
                                text: node.textContent.trim(),
                                parentTag: parent.tagName,
                                parentClass: parent.className,
                                parentId: parent.id,
                                fullHtml: parent.outerHTML.substring(0, 500)
                            });
                        }
                    }
                    
                    return reviewTexts.slice(0, 20); // Return first 20 potential reviews
                }
            """)
            
            logger.info("Potential review content found:")
            for i, review in enumerate(review_content):
                logger.info(f"\n{i+1}. Text: {review['text'][:100]}")
                logger.info(f"    Parent: {review['parentTag']}.{review['parentClass']}")
                logger.info(f"    HTML: {review['fullHtml'][:200]}")
            
            # Check if this is actually showing individual reviews or just the summary
            page_text = await page.inner_text('body')
            
            # Look for review indicators
            if 'individual review' in page_text.lower() or 'posted' in page_text.lower():
                logger.info("Found individual reviews on page")
            else:
                logger.info("This might be a reviews summary page, not individual reviews")
                
                # Try to find a link to actual reviews
                review_links = await page.evaluate("""
                    () => {
                        const links = Array.from(document.querySelectorAll('a'));
                        return links
                            .filter(link => 
                                link.textContent.toLowerCase().includes('review') ||
                                link.href.includes('review')
                            )
                            .map(link => ({
                                text: link.textContent.trim(),
                                href: link.href,
                                className: link.className
                            }))
                            .slice(0, 10);
                    }
                """)
                
                logger.info("Found review-related links:")
                for link in review_links:
                    logger.info(f"  '{link['text']}' -> {link['href']}")
            
            # Try scrolling to see if more content loads
            logger.info("Trying to scroll and find review content...")
            
            # Scroll down to see if reviews load
            for i in range(5):
                await page.evaluate("window.scrollBy(0, 1000)")
                await page.wait_for_timeout(2000)
                
                # Check for new content
                new_count = await page.locator('*:has-text("ago")').count()
                logger.info(f"After scroll {i+1}: Found {new_count} elements with 'ago'")
            
            # Try to get all links to see page structure
            all_page_urls = await page.evaluate("""
                () => {
                    const links = Array.from(document.querySelectorAll('a[href]'));
                    const urls = new Set();
                    
                    links.forEach(link => {
                        if (link.href.includes('reviews')) {
                            urls.add(link.href);
                        }
                    });
                    
                    return Array.from(urls);
                }
            """)
            
            logger.info("All review-related URLs found on page:")
            for url in all_page_urls:
                logger.info(f"  {url}")
            
        except Exception as e:
            logger.error(f"Error: {e}")
        
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(extract_review_structure())