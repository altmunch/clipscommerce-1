#!/usr/bin/env python3
"""
Simplified test script to investigate Shopify reviews page structure
"""

import asyncio
import logging
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_shopify_selectors():
    """Test specific selectors for Shopify reviews"""
    
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
            
            # Wait for page to settle
            await page.wait_for_timeout(3000)
            
            # Get page title to confirm we're on the right page
            title = await page.title()
            logger.info(f"Page title: {title}")
            
            # Test the original failing selector
            logger.info("Testing original selector: [data-testid=\"reviews-list\"] .ui-app-review-card")
            original_selector = '[data-testid="reviews-list"] .ui-app-review-card'
            original_count = await page.locator(original_selector).count()
            logger.info(f"Original selector found: {original_count} elements")
            
            # Test alternative selectors step by step
            selectors_to_test = [
                # Data-testid based
                '[data-testid="reviews-list"]',
                '.ui-app-review-card',
                '[data-testid="app-review-business-name"]',
                '[data-testid="app-review-author-name"]',
                '[data-testid="app-review-posted-date"]',
                '[data-testid="app-review-star-rating"]',
                '[data-testid="app-review-body"]',
                
                # Common review patterns
                '.review',
                '.review-card',
                '.review-item',
                '[class*="review" i]',  # case insensitive
                
                # List item patterns
                'article',
                'li',
                '.list-item',
                
                # Get all divs that might contain review content
                'div[class*="card" i]',
                'div[class*="item" i]',
                
                # Look for specific content patterns
                '*:has-text("ago")',  # Reviews typically have "X days ago"
                '*:has-text("stars")',  # Star ratings
            ]
            
            for selector in selectors_to_test:
                try:
                    count = await page.locator(selector).count()
                    if count > 0:
                        logger.info(f"✓ {selector}: {count} elements")
                        
                        # Get sample text from first element
                        try:
                            first_text = await page.locator(selector).first.inner_text()
                            preview = first_text[:150].replace('\n', ' ')
                            logger.info(f"  Sample: {preview}")
                        except:
                            pass
                    
                except Exception as e:
                    logger.debug(f"Error with {selector}: {e}")
            
            # Get raw HTML structure to analyze
            logger.info("Getting main content structure...")
            
            # Find the main content area
            main_content = await page.evaluate("""
                () => {
                    // Look for main content containers
                    const selectors = ['main', '[role="main"]', '.main', '#main', '.content'];
                    
                    for (const sel of selectors) {
                        const el = document.querySelector(sel);
                        if (el) {
                            return {
                                tagName: el.tagName,
                                className: el.className,
                                innerHTML: el.innerHTML.substring(0, 2000)
                            };
                        }
                    }
                    
                    // Fallback to body content
                    const body = document.body;
                    return {
                        tagName: 'BODY',
                        className: body.className,
                        innerHTML: body.innerHTML.substring(0, 2000)
                    };
                }
            """)
            
            logger.info(f"Main content tag: {main_content['tagName']}")
            logger.info(f"Main content class: {main_content['className']}")
            
            # Look for review-like content in the HTML
            review_patterns = await page.evaluate("""
                () => {
                    const html = document.body.innerHTML;
                    const patterns = [];
                    
                    // Look for common review-related strings
                    const reviewKeywords = [
                        'review', 'rating', 'star', 'feedback', 'merchant',
                        'store', 'business', 'author', 'posted', 'ago'
                    ];
                    
                    reviewKeywords.forEach(keyword => {
                        const regex = new RegExp(`(class|data-[^=]*)="[^"]*${keyword}[^"]*"`, 'gi');
                        const matches = html.match(regex);
                        if (matches) {
                            patterns.push({
                                keyword: keyword,
                                matches: matches.slice(0, 5)  // First 5 matches
                            });
                        }
                    });
                    
                    return patterns;
                }
            """)
            
            logger.info("Review-related patterns found in HTML:")
            for pattern in review_patterns:
                logger.info(f"  {pattern['keyword']}: {pattern['matches']}")
            
            # Check if we can find pagination or load more buttons
            pagination_selectors = [
                '[data-testid="load-more-reviews-button"]',
                '.load-more',
                '.pagination',
                'button:has-text("Load more")',
                'button:has-text("Next")',
                'a:has-text("Next")',
            ]
            
            logger.info("Checking for pagination/load more...")
            for selector in pagination_selectors:
                try:
                    count = await page.locator(selector).count()
                    if count > 0:
                        logger.info(f"✓ Found pagination: {selector} ({count} elements)")
                except:
                    pass
            
        except Exception as e:
            logger.error(f"Error: {e}")
        
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_shopify_selectors())