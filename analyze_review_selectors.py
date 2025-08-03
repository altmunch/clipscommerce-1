#!/usr/bin/env python3
"""
Analyze the exact structure of Shopify reviews to identify correct selectors
"""

import asyncio
import logging
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def analyze_review_selectors():
    """Analyze the exact structure of reviews to identify proper selectors"""
    
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
            
            # Now let's analyze the HTML structure more systematically
            logger.info("Analyzing review structure...")
            
            # Find all elements that contain review-like text and their containers
            review_analysis = await page.evaluate("""
                () => {
                    const results = [];
                    
                    // Look for elements that contain review text patterns
                    const reviewPatterns = [
                        /using the app/i,
                        /years? (using|with)/i,
                        /months? (using|with)/i,
                        /this app/i,
                        /highly recommend/i,
                        /great app/i,
                        /best.*app/i,
                        /love this/i,
                        /customer service/i,
                        /support/i
                    ];
                    
                    const walker = document.createTreeWalker(
                        document.body,
                        NodeFilter.SHOW_ELEMENT,
                        {
                            acceptNode: function(node) {
                                const text = node.textContent || '';
                                if (text.length > 20 && text.length < 1000) {
                                    for (const pattern of reviewPatterns) {
                                        if (pattern.test(text)) {
                                            return NodeFilter.FILTER_ACCEPT;
                                        }
                                    }
                                }
                                return NodeFilter.FILTER_SKIP;
                            }
                        }
                    );
                    
                    let node;
                    while (node = walker.nextNode()) {
                        const text = node.textContent.trim();
                        
                        // Find the container that likely holds the full review
                        let container = node;
                        while (container.parentElement) {
                            const parent = container.parentElement;
                            const parentText = parent.textContent.trim();
                            
                            // If parent has significantly more text, it might be the review container
                            if (parentText.length > text.length * 1.2 && parentText.length < text.length * 3) {
                                container = parent;
                            } else {
                                break;
                            }
                        }
                        
                        // Get the path to this element
                        const getPath = (el) => {
                            const path = [];
                            while (el && el !== document.body) {
                                let selector = el.tagName.toLowerCase();
                                if (el.id) {
                                    selector += '#' + el.id;
                                }
                                if (el.className) {
                                    const classes = el.className.split(' ').filter(c => c).slice(0, 3);
                                    if (classes.length > 0) {
                                        selector += '.' + classes.join('.');
                                    }
                                }
                                path.unshift(selector);
                                el = el.parentElement;
                            }
                            return path.join(' > ');
                        };
                        
                        results.push({
                            text: text.substring(0, 200),
                            containerText: container.textContent.trim().substring(0, 500),
                            elementTag: node.tagName,
                            elementClass: node.className,
                            containerTag: container.tagName,
                            containerClass: container.className,
                            path: getPath(container),
                            attributes: Array.from(container.attributes).map(attr => attr.name + '=' + attr.value)
                        });
                    }
                    
                    return results.slice(0, 10); // Top 10 results
                }
            """)
            
            logger.info("Review element analysis:")
            for i, review in enumerate(review_analysis):
                logger.info(f"\n{i+1}. Review text: {review['text'][:100]}...")
                logger.info(f"    Element: {review['elementTag']}.{review['elementClass']}")
                logger.info(f"    Container: {review['containerTag']}.{review['containerClass']}")
                logger.info(f"    Path: {review['path']}")
                logger.info(f"    Attributes: {review['attributes'][:3]}")  # First 3 attributes
            
            # Now let's find the common parent structure
            common_patterns = await page.evaluate("""
                () => {
                    // Find all text that looks like review text
                    const reviewTexts = Array.from(document.querySelectorAll('*')).filter(el => {
                        const text = el.textContent.trim();
                        return text.length > 50 && text.length < 1000 && (
                            text.includes('using the app') ||
                            text.includes('this app') ||
                            text.includes('recommend') ||
                            text.includes('great') ||
                            text.includes('love')
                        );
                    });
                    
                    // Group by common parent structure
                    const patterns = {};
                    
                    reviewTexts.forEach(el => {
                        let parent = el.parentElement;
                        while (parent && parent !== document.body) {
                            const key = parent.tagName + '.' + parent.className;
                            if (!patterns[key]) {
                                patterns[key] = {
                                    selector: key,
                                    count: 0,
                                    examples: []
                                };
                            }
                            patterns[key].count++;
                            if (patterns[key].examples.length < 3) {
                                patterns[key].examples.push(parent.textContent.trim().substring(0, 150));
                            }
                            parent = parent.parentElement;
                        }
                    });
                    
                    // Return patterns sorted by count
                    return Object.values(patterns)
                        .sort((a, b) => b.count - a.count)
                        .slice(0, 10);
                }
            """)
            
            logger.info("\\nCommon parent patterns for reviews:")
            for pattern in common_patterns:
                logger.info(f"  {pattern['selector']}: {pattern['count']} occurrences")
                logger.info(f"    Examples: {pattern['examples'][:2]}")
            
            # Try to find specific field patterns
            field_patterns = await page.evaluate("""
                () => {
                    const patterns = {
                        storeNames: [],
                        reviewerNames: [],
                        dates: [],
                        ratings: [],
                        reviewBodies: []
                    };
                    
                    // Look for store/business names (typically near reviews)
                    const businessElements = Array.from(document.querySelectorAll('*')).filter(el => {
                        const text = el.textContent.trim();
                        return text.length < 100 && text.length > 3 && (
                            el.className.toLowerCase().includes('business') ||
                            el.className.toLowerCase().includes('store') ||
                            el.className.toLowerCase().includes('merchant') ||
                            (text && !text.includes(' ') && text.length < 50 && /^[A-Z]/.test(text))
                        );
                    });
                    
                    businessElements.slice(0, 5).forEach(el => {
                        patterns.storeNames.push({
                            text: el.textContent.trim(),
                            selector: el.tagName + '.' + el.className,
                            attributes: Array.from(el.attributes).map(attr => attr.name)
                        });
                    });
                    
                    // Look for time indicators (dates)
                    const timeElements = Array.from(document.querySelectorAll('*')).filter(el => {
                        const text = el.textContent.trim();
                        return text.includes('year') || text.includes('month') || text.includes('ago') || text.includes('using');
                    });
                    
                    timeElements.slice(0, 5).forEach(el => {
                        patterns.dates.push({
                            text: el.textContent.trim(),
                            selector: el.tagName + '.' + el.className,
                            attributes: Array.from(el.attributes).map(attr => attr.name)
                        });
                    });
                    
                    // Look for star ratings
                    const ratingElements = Array.from(document.querySelectorAll('*')).filter(el => {
                        return el.className.toLowerCase().includes('star') || 
                               el.textContent.includes('star') ||
                               el.className.toLowerCase().includes('rating');
                    });
                    
                    ratingElements.slice(0, 5).forEach(el => {
                        patterns.ratings.push({
                            text: el.textContent.trim().substring(0, 50),
                            selector: el.tagName + '.' + el.className,
                            attributes: Array.from(el.attributes).map(attr => attr.name)
                        });
                    });
                    
                    return patterns;
                }
            """)
            
            logger.info("\\nField-specific patterns:")
            logger.info("Store/Business names:")
            for name in field_patterns['storeNames']:
                logger.info(f"  '{name['text']}' -> {name['selector']}")
            
            logger.info("\\nDate/Time patterns:")
            for date in field_patterns['dates']:
                logger.info(f"  '{date['text']}' -> {date['selector']}")
            
            logger.info("\\nRating patterns:")
            for rating in field_patterns['ratings']:
                logger.info(f"  '{rating['text']}' -> {rating['selector']}")
            
        except Exception as e:
            logger.error(f"Error: {e}")
        
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(analyze_review_selectors())