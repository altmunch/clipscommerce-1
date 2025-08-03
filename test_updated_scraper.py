#!/usr/bin/env python3
"""
Test the updated Shopify scraper with working app URLs
"""

import asyncio
import sys
sys.path.append('/workspaces/api/shopify_app_store_scraper')

from shopify_review_scraper import ShopifyReviewScraper
from playwright.async_api import async_playwright

async def test_updated_scraper():
    """Test the updated scraper with a known working URL"""
    
    # Test with Klaviyo since we know it works
    test_url = "https://apps.shopify.com/klaviyo-email-marketing/reviews"
    
    scraper = ShopifyReviewScraper()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        try:
            print(f"Testing updated scraper with: {test_url}")
            await scraper.scrape_url(browser, test_url)
            
            print(f"\nResults:")
            print(f"Total reviews found: {len(scraper.reviews)}")
            
            # Show first few reviews
            for i, review in enumerate(scraper.reviews[:5]):
                print(f"\nReview {i+1}:")
                print(f"  Store: {review.store_name}")
                print(f"  Reviewer: {review.reviewer_name}")
                print(f"  Date: {review.review_date}")
                print(f"  Rating: {review.review_rating}")
                print(f"  Text: {review.review_text[:100]}...")
            
            if len(scraper.reviews) > 5:
                print(f"\n... and {len(scraper.reviews) - 5} more reviews")
                
        except Exception as e:
            print(f"Error: {e}")
            
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_updated_scraper())