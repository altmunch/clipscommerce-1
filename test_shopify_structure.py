#!/usr/bin/env python3
"""
Test script to investigate current Shopify App Store structure
and identify working CSS selectors for review scraping.
"""

import asyncio
import logging
from playwright.async_api import async_playwright

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def investigate_shopify_structure():
    """Investigate the current Shopify App Store page structure"""
    
    # Test with a known working app
    test_url = "https://apps.shopify.com/klaviyo-email-marketing/reviews"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)  # Run in headless mode
        page = await browser.new_page()
        
        try:
            # Set user agent
            await page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            logger.info(f"Navigating to: {test_url}")
            await page.goto(test_url, wait_until='networkidle', timeout=30000)
            
            # Wait a bit for any dynamic content
            await page.wait_for_timeout(3000)
            
            # Take a screenshot for manual inspection
            await page.screenshot(path="shopify_reviews_page.png", full_page=True)
            logger.info("Screenshot saved as shopify_reviews_page.png")
            
            # Try different potential selectors for reviews
            potential_selectors = [
                # Original selectors
                '[data-testid="reviews-list"] .ui-app-review-card',
                '.ui-app-review-card',
                '[data-testid="app-review-business-name"]',
                
                # Alternative common patterns
                '.review',
                '.review-card',
                '.app-review',
                '[class*="review"]',
                '[class*="Review"]',
                
                # Generic review patterns
                'article',
                '.review-item',
                '.review-container',
                '[data-review]',
                
                # Shopify specific patterns
                '.ui-review',
                '.shopify-review',
                '.merchant-review',
                
                # List-based patterns
                'ul li',
                '.list-item',
                
                # Modern CSS patterns
                '[role="article"]',
                '[aria-label*="review"]',
                
                # Container patterns
                'main section',
                '.content section',
                '.reviews section'
            ]
            
            logger.info("Testing potential review container selectors...")
            
            for selector in potential_selectors:
                try:
                    elements = await page.locator(selector).count()
                    if elements > 0:
                        logger.info(f"✓ Found {elements} elements with selector: {selector}")
                        
                        # Get sample content from first element
                        if elements > 0:
                            try:
                                sample_text = await page.locator(selector).first.inner_text()
                                sample_text = sample_text[:100] + "..." if len(sample_text) > 100 else sample_text
                                logger.info(f"  Sample text: {sample_text}")
                            except:
                                pass
                    else:
                        logger.debug(f"✗ No elements found for: {selector}")
                except Exception as e:
                    logger.debug(f"✗ Error testing {selector}: {e}")
            
            # Get page HTML structure for analysis
            logger.info("Extracting page structure...")
            
            # Get all elements with class or data attributes that might contain reviews
            review_elements = await page.evaluate("""
                () => {
                    const elements = [];
                    const all = document.querySelectorAll('*');
                    
                    for (let el of all) {
                        // Look for elements that might be reviews
                        const className = el.className || '';
                        const dataAttrs = Array.from(el.attributes)
                            .filter(attr => attr.name.startsWith('data-'))
                            .map(attr => attr.name + '=' + attr.value);
                        
                        if (className.toLowerCase().includes('review') || 
                            dataAttrs.some(attr => attr.toLowerCase().includes('review')) ||
                            el.textContent.includes('stars') ||
                            el.textContent.includes('ago') ||
                            (el.tagName === 'ARTICLE' && el.textContent.length > 50)) {
                            
                            elements.push({
                                tagName: el.tagName,
                                className: className,
                                dataAttributes: dataAttrs,
                                textPreview: el.textContent.substring(0, 100),
                                selector: el.tagName.toLowerCase() + 
                                         (el.id ? '#' + el.id : '') + 
                                         (className ? '.' + className.split(' ').join('.') : '')
                            });
                        }
                    }
                    
                    return elements.slice(0, 20); // Return top 20 matches
                }
            """)
            
            logger.info("Potential review elements found:")
            for i, element in enumerate(review_elements):
                logger.info(f"{i+1}. Tag: {element['tagName']}, Class: {element['className']}")
                logger.info(f"   Data attrs: {element['dataAttributes']}")
                logger.info(f"   Text: {element['textPreview']}")
                logger.info(f"   Selector: {element['selector']}")
                logger.info("---")
            
            # Try to identify the main content area
            main_content_selectors = ['main', '[role="main"]', '.main-content', '#main', '.content']
            for selector in main_content_selectors:
                try:
                    if await page.locator(selector).count() > 0:
                        logger.info(f"Found main content area: {selector}")
                        break
                except:
                    pass
            
        except Exception as e:
            logger.error(f"Error investigating page structure: {e}")
        
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(investigate_shopify_structure())