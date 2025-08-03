#!/usr/bin/env python3
"""
Quick debug script to check current Shopify App Store structure
"""

import asyncio
from playwright.async_api import async_playwright


async def debug_page_structure():
    """Debug a specific Shopify App Store page structure"""
    
    # Test with a known working app URL
    test_url = "https://apps.shopify.com/klaviyo-email-marketing/reviews"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print(f"Navigating to: {test_url}")
        await page.goto(test_url, wait_until='networkidle', timeout=30000)
        
        # Wait a moment for page to fully load
        await page.wait_for_timeout(3000)
        
        # Check various possible review selectors
        selectors_to_test = [
            'div[data-merchant-review]',
            '.tw-pb-md.md\\:tw-pb-lg .tw-mb-md',
            '[data-testid="reviews-list"] .ui-app-review-card',
            '.review-card',
            '[data-review]',
            '[class*="review"]',
            'article',
            '.review'
        ]
        
        print("\nTesting selectors:")
        for selector in selectors_to_test:
            try:
                count = await page.locator(selector).count()
                print(f"  {selector}: {count} elements")
                if count > 0:
                    # Get first element text preview
                    first_text = await page.locator(selector).first.inner_text()
                    print(f"    Preview: {first_text[:100]}...")
            except Exception as e:
                print(f"  {selector}: ERROR - {e}")
        
        # Check page title and URL to ensure we're on the right page
        title = await page.title()
        current_url = page.url
        print(f"\nPage title: {title}")
        print(f"Current URL: {current_url}")
        
        # Take a screenshot for manual inspection
        await page.screenshot(path='shopify_debug.png')
        print("\nScreenshot saved as 'shopify_debug.png'")
        
        await browser.close()


if __name__ == "__main__":
    asyncio.run(debug_page_structure())