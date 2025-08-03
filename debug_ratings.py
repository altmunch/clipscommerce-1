#!/usr/bin/env python3
"""
Debug rating extraction from Shopify reviews
"""

import asyncio
from playwright.async_api import async_playwright

async def debug_ratings():
    """Debug the rating extraction"""
    
    test_url = "https://apps.shopify.com/klaviyo-email-marketing/reviews"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            await page.goto(test_url, wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(3000)
            
            # Find rating elements in the review containers
            rating_analysis = await page.evaluate("""
                () => {
                    const reviewContainers = document.querySelectorAll('div[data-merchant-review]');
                    const results = [];
                    
                    for (let i = 0; i < Math.min(5, reviewContainers.length); i++) {
                        const container = reviewContainers[i];
                        
                        // Look for any rating-related elements
                        const potentialRatingElements = Array.from(container.querySelectorAll('*')).filter(el => {
                            const text = el.textContent || '';
                            const className = el.className || '';
                            const ariaLabel = el.getAttribute('aria-label') || '';
                            
                            return (
                                className.toLowerCase().includes('star') ||
                                className.toLowerCase().includes('rating') ||
                                ariaLabel.toLowerCase().includes('star') ||
                                ariaLabel.toLowerCase().includes('rating') ||
                                text.includes('star') ||
                                text.includes('rating')
                            );
                        });
                        
                        results.push({
                            reviewIndex: i,
                            ratingElements: potentialRatingElements.map(el => ({
                                tagName: el.tagName,
                                className: el.className,
                                ariaLabel: el.getAttribute('aria-label'),
                                textContent: el.textContent.trim(),
                                innerHTML: el.innerHTML.substring(0, 200)
                            }))
                        });
                    }
                    
                    return results;
                }
            """)
            
            print("Rating analysis for first 5 reviews:")
            for result in rating_analysis:
                print(f"\nReview {result['reviewIndex'] + 1}:")
                if result['ratingElements']:
                    for i, elem in enumerate(result['ratingElements']):
                        print(f"  Element {i+1}: {elem['tagName']}.{elem['className']}")
                        print(f"    Text: '{elem['textContent']}'")
                        print(f"    Aria: '{elem['ariaLabel']}'")
                        print(f"    HTML: {elem['innerHTML'][:100]}...")
                else:
                    print("  No rating elements found")
            
            # Also check for any overall rating indicators
            overall_rating = await page.evaluate("""
                () => {
                    const ratingElements = Array.from(document.querySelectorAll('*')).filter(el => {
                        const text = el.textContent || '';
                        return text.includes('4.7') || text.includes('rating') || text.includes('Overall');
                    });
                    
                    return ratingElements.slice(0, 5).map(el => ({
                        tagName: el.tagName,
                        className: el.className,
                        textContent: el.textContent.trim().substring(0, 100),
                        ariaLabel: el.getAttribute('aria-label')
                    }));
                }
            """)
            
            print("\nOverall rating elements found:")
            for elem in overall_rating:
                print(f"  {elem['tagName']}.{elem['className']}: '{elem['textContent']}'")
            
        except Exception as e:
            print(f"Error: {e}")
        
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_ratings())