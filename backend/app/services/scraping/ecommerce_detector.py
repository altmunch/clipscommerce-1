"""
E-commerce platform detection and specialized scraping strategies.
"""

import re
from typing import Dict, List, Optional, Set
from urllib.parse import urlparse
import logging

from bs4 import BeautifulSoup
from selectolax.parser import HTMLParser

logger = logging.getLogger(__name__)


class EcommerceDetector:
    """Detects e-commerce platforms and provides platform-specific scraping strategies"""
    
    # Platform detection patterns
    PLATFORM_SIGNATURES = {
        "shopify": {
            "meta_tags": ["Shopify"],
            "scripts": ["cdn.shopify.com", "shopifycdn.com"],
            "css": ["shopify"],
            "html_patterns": ["shopify-section", "shopify-pay"],
            "urls": ["/cart/add", "/products/", "/collections/"],
            "generators": ["Shopify"]
        },
        "woocommerce": {
            "meta_tags": ["WooCommerce"],
            "scripts": ["woocommerce", "wc-"],
            "css": ["woocommerce", "wc-"],
            "html_patterns": ["woocommerce", "wc-"],
            "urls": ["/cart/", "/checkout/", "/my-account/"],
            "generators": ["WooCommerce"]
        },
        "bigcommerce": {
            "meta_tags": ["BigCommerce"],
            "scripts": ["bigcommerce.com", "bc-sf-filter"],
            "css": ["bigcommerce"],
            "html_patterns": ["bigcommerce"],
            "urls": ["/cart.php", "/checkout/"],
            "generators": ["BigCommerce"]
        },
        "magento": {
            "meta_tags": ["Magento"],
            "scripts": ["mage/", "magento"],
            "css": ["magento"],
            "html_patterns": ["magento", "mage-"],
            "urls": ["/checkout/cart/", "/customer/account/"],
            "generators": ["Magento"]
        },
        "prestashop": {
            "meta_tags": ["PrestaShop"],
            "scripts": ["prestashop", "ps_"],
            "css": ["prestashop"],
            "html_patterns": ["prestashop"],
            "urls": ["/order", "/authentication"],
            "generators": ["PrestaShop"]
        },
        "squarespace": {
            "meta_tags": ["Squarespace"],
            "scripts": ["squarespace.com", "static1.squarespace.com"],
            "css": ["squarespace"],
            "html_patterns": ["squarespace"],
            "urls": [],
            "generators": ["Squarespace"]
        },
        "wix": {
            "meta_tags": ["Wix.com"],
            "scripts": ["wix.com", "wixstatic.com"],
            "css": ["wix"],
            "html_patterns": ["wix"],
            "urls": [],
            "generators": ["Wix"]
        },
        "square": {
            "meta_tags": ["Square"],
            "scripts": ["squareup.com", "square"],
            "css": ["square"],
            "html_patterns": ["square"],
            "urls": [],
            "generators": ["Square"]
        }
    }
    
    # Product selectors for different platforms
    PRODUCT_SELECTORS = {
        "shopify": {
            "product_container": [".product", ".product-form", "[data-product-id]"],
            "title": [".product-title", ".product__title", "h1.product-single__title"],
            "price": [".price", ".product-price", "[data-price]", ".product__price"],
            "description": [".product-description", ".product__description", ".rte"],
            "images": [".product-image img", ".product__media img", ".product-photo img"],
            "variants": [".product-variants", ".product-form__variants", "[data-variant]"],
            "availability": [".product-availability", "[data-inventory]"],
            "reviews": [".reviews", ".product-reviews", "[data-reviews]"]
        },
        "woocommerce": {
            "product_container": [".product", ".single-product"],
            "title": [".product_title", ".entry-title"],
            "price": [".price", ".woocommerce-Price-amount"],
            "description": [".woocommerce-product-details__short-description", ".product_meta"],
            "images": [".woocommerce-product-gallery img", ".product-image img"],
            "variants": [".variations", ".variable-product"],
            "availability": [".stock", ".out-of-stock"],
            "reviews": [".woocommerce-reviews", "#reviews"]
        },
        "bigcommerce": {
            "product_container": [".product", ".productView"],
            "title": [".product-title", ".productView-title"],
            "price": [".price", ".productView-price"],
            "description": [".product-description", ".productView-description"],
            "images": [".product-image img", ".productView-image img"],
            "variants": [".product-options", ".form-field"],
            "availability": [".product-availability"],
            "reviews": [".reviews", ".productView-reviews"]
        },
        "magento": {
            "product_container": [".product-info-main", ".product.info"],
            "title": [".page-title", ".product-item-name"],
            "price": [".price", ".price-box"],
            "description": [".product.attribute.description", ".product-info-description"],
            "images": [".product-image-main img", ".gallery-image img"],
            "variants": [".swatch-attribute", ".product-options-wrapper"],
            "availability": [".stock", ".availability"],
            "reviews": [".reviews", ".product-reviews"]
        },
        "generic": {
            "product_container": [".product", "[data-product]", ".item"],
            "title": ["h1", ".title", ".product-title", ".name"],
            "price": [".price", ".cost", ".amount", "[data-price]"],
            "description": [".description", ".details", ".summary"],
            "images": [".product-image img", ".gallery img", ".main-image img"],
            "variants": [".options", ".variants", ".attributes"],
            "availability": [".stock", ".availability", ".in-stock"],
            "reviews": [".reviews", ".ratings", ".testimonials"]
        }
    }
    
    def __init__(self):
        self.detected_platforms: Set[str] = set()
        self.confidence_scores: Dict[str, float] = {}
    
    def detect_platform(self, soup: BeautifulSoup, url: str) -> Dict[str, any]:
        """Detect e-commerce platform from HTML content"""
        
        results = {
            "platforms": [],
            "primary_platform": None,
            "confidence": 0.0,
            "features": [],
            "selectors": {}
        }
        
        # Get page content as string for pattern matching
        html_content = str(soup).lower()
        
        platform_scores = {}
        
        for platform, signatures in self.PLATFORM_SIGNATURES.items():
            score = 0
            found_features = []
            
            # Check meta tags
            for meta_pattern in signatures.get("meta_tags", []):
                if soup.find("meta", attrs={"name": "generator", "content": re.compile(meta_pattern, re.I)}):
                    score += 3
                    found_features.append(f"meta_{meta_pattern}")
            
            # Check script sources
            for script_pattern in signatures.get("scripts", []):
                scripts = soup.find_all("script", src=True)
                for script in scripts:
                    if script_pattern.lower() in script["src"].lower():
                        score += 2
                        found_features.append(f"script_{script_pattern}")
                        break
            
            # Check CSS links
            for css_pattern in signatures.get("css", []):
                links = soup.find_all("link", href=True)
                for link in links:
                    if css_pattern.lower() in link["href"].lower():
                        score += 2
                        found_features.append(f"css_{css_pattern}")
                        break
            
            # Check HTML patterns
            for html_pattern in signatures.get("html_patterns", []):
                if html_pattern.lower() in html_content:
                    score += 1
                    found_features.append(f"html_{html_pattern}")
            
            # Check URL patterns
            for url_pattern in signatures.get("urls", []):
                if url_pattern in url.lower():
                    score += 1
                    found_features.append(f"url_{url_pattern}")
            
            if score > 0:
                platform_scores[platform] = {
                    "score": score,
                    "features": found_features
                }
        
        # Sort platforms by score
        sorted_platforms = sorted(platform_scores.items(), key=lambda x: x[1]["score"], reverse=True)
        
        if sorted_platforms:
            primary_platform = sorted_platforms[0][0]
            primary_score = sorted_platforms[0][1]["score"]
            
            results["platforms"] = [p[0] for p in sorted_platforms]
            results["primary_platform"] = primary_platform
            results["confidence"] = min(primary_score / 10.0, 1.0)  # Normalize to 0-1
            results["features"] = sorted_platforms[0][1]["features"]
            results["selectors"] = self.PRODUCT_SELECTORS.get(primary_platform, self.PRODUCT_SELECTORS["generic"])
        else:
            # Default to generic selectors
            results["selectors"] = self.PRODUCT_SELECTORS["generic"]
        
        return results
    
    def get_product_selectors(self, platform: str = None) -> Dict[str, List[str]]:
        """Get product selectors for specific platform"""
        if platform and platform in self.PRODUCT_SELECTORS:
            return self.PRODUCT_SELECTORS[platform]
        return self.PRODUCT_SELECTORS["generic"]
    
    def detect_product_listing_patterns(self, soup: BeautifulSoup) -> Dict[str, List[str]]:
        """Detect product listing patterns on category/collection pages"""
        
        patterns = {
            "product_items": [],
            "pagination": [],
            "filters": [],
            "sort_options": []
        }
        
        # Common product item selectors
        product_item_selectors = [
            ".product-item", ".product-card", ".item", 
            "[data-product-id]", ".product-grid-item",
            ".product-list-item", ".product"
        ]
        
        for selector in product_item_selectors:
            elements = soup.select(selector)
            if len(elements) > 3:  # Likely a product listing if multiple items
                patterns["product_items"].append(selector)
        
        # Pagination patterns
        pagination_selectors = [
            ".pagination", ".pager", ".page-numbers",
            "[data-pagination]", ".next-page", ".prev-page"
        ]
        
        for selector in pagination_selectors:
            if soup.select(selector):
                patterns["pagination"].append(selector)
        
        # Filter patterns
        filter_selectors = [
            ".filters", ".facets", ".sidebar-filters",
            ".product-filters", "[data-filter]"
        ]
        
        for selector in filter_selectors:
            if soup.select(selector):
                patterns["filters"].append(selector)
        
        # Sort options
        sort_selectors = [
            ".sort-by", ".product-sort", "[data-sort]",
            ".sort-options", "select[name*='sort']"
        ]
        
        for selector in sort_selectors:
            if soup.select(selector):
                patterns["sort_options"].append(selector)
        
        return patterns
    
    def is_product_page(self, soup: BeautifulSoup, url: str) -> Dict[str, any]:
        """Determine if current page is a product page"""
        
        indicators = {
            "is_product": False,
            "confidence": 0.0,
            "signals": []
        }
        
        score = 0
        signals = []
        
        # URL patterns for product pages
        product_url_patterns = [
            r'/product/', r'/products/', r'/item/', r'/p/',
            r'-p-\d+', r'/dp/', r'/gp/product/'
        ]
        
        for pattern in product_url_patterns:
            if re.search(pattern, url, re.I):
                score += 2
                signals.append(f"url_pattern_{pattern}")
        
        # Check for price elements
        price_selectors = [
            ".price", "[data-price]", ".cost", ".amount",
            ".product-price", ".price-current"
        ]
        
        for selector in price_selectors:
            if soup.select(selector):
                score += 1
                signals.append(f"price_element_{selector}")
        
        # Check for add to cart buttons
        cart_selectors = [
            "[data-add-to-cart]", ".add-to-cart", ".buy-now",
            "button[name='add']", ".purchase-button"
        ]
        
        for selector in cart_selectors:
            if soup.select(selector):
                score += 2
                signals.append(f"cart_button_{selector}")
        
        # Check for product variants/options
        variant_selectors = [
            ".variants", ".options", ".attributes",
            "select[name*='variant']", ".product-options"
        ]
        
        for selector in variant_selectors:
            if soup.select(selector):
                score += 1
                signals.append(f"variants_{selector}")
        
        # Check for product images gallery
        gallery_selectors = [
            ".product-gallery", ".product-images", ".image-gallery",
            ".product-photos"
        ]
        
        for selector in gallery_selectors:
            if soup.select(selector):
                score += 1
                signals.append(f"gallery_{selector}")
        
        # Check schema.org Product markup
        json_ld_scripts = soup.find_all("script", type="application/ld+json")
        for script in json_ld_scripts:
            try:
                import json
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get("@type") == "Product":
                    score += 3
                    signals.append("schema_product")
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get("@type") == "Product":
                            score += 3
                            signals.append("schema_product")
                            break
            except:
                pass
        
        indicators["is_product"] = score >= 3
        indicators["confidence"] = min(score / 10.0, 1.0)
        indicators["signals"] = signals
        
        return indicators
    
    def get_platform_specific_config(self, platform: str) -> Dict[str, any]:
        """Get platform-specific scraping configuration"""
        
        configs = {
            "shopify": {
                "api_endpoints": {
                    "products": "/products.json",
                    "collections": "/collections.json",
                    "product": "/products/{handle}.json"
                },
                "rate_limit": 2,  # requests per second
                "special_handling": {
                    "variants": True,
                    "metafields": True,
                    "collections": True
                }
            },
            "woocommerce": {
                "api_endpoints": {
                    "products": "/wp-json/wc/v3/products",
                    "categories": "/wp-json/wc/v3/products/categories"
                },
                "rate_limit": 1,
                "special_handling": {
                    "rest_api": True,
                    "auth_required": True
                }
            },
            "bigcommerce": {
                "api_endpoints": {
                    "products": "/api/storefront/products"
                },
                "rate_limit": 1,
                "special_handling": {
                    "graphql": True,
                    "auth_required": True
                }
            }
        }
        
        return configs.get(platform, {
            "api_endpoints": {},
            "rate_limit": 1,
            "special_handling": {}
        })