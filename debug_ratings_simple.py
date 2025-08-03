#!/usr/bin/env python3
"""
Simple debug for rating extraction
"""

import asyncio
from playwright.async_api import async_playwright

async def debug_ratings_simple():
    """Simple rating debug"""
    
    test_url = "https://apps.shopify.com/klaviyo-email-marketing/reviews"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            await page.goto(test_url, wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(3000)
            
            # Check the first review container for rating elements
            review_locator = page.locator('div[data-merchant-review]')
            
            if await review_locator.count() > 0:
                first_review = review_locator.first
                print("Found review container, checking for rating elements...")
                
                # Try different rating selectors
                rating_selectors = [
                    '[class*="star"]',
                    '[aria-label*="star"]',
                    '[title*="star"]',
                    '.rating',
                    '[class*="rating"]',
                    'svg',
                    '[role="img"]'
                ]
                
                for selector in rating_selectors:
                    try:
                        count = await first_review.locator(selector).count()
                        if count > 0:
                            print(f"Found {count} elements with selector: {selector}")
                            # Get the first element's details
                            first_elem = first_review.locator(selector).first
                            text = await first_elem.inner_text() if await first_elem.count() > 0 else ""
                            print(f"  First element text: '{text}'")
                    except:
                        pass
                
                # Get the HTML content of the review to see the structure
                html_content = await first_review.inner_html()
                print(f"\nFirst review HTML (first 500 chars):")
                print(html_content[:500])
                
            else:
                print("No review containers found")
                
        except Exception as e:
            print(f"Error: {e}")
        
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_ratings_simple())