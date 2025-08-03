"""
Specialized product scraper for extracting detailed product information from e-commerce sites.
"""

import re
import json
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin, urlparse
from decimal import Decimal, InvalidOperation
import logging

from bs4 import BeautifulSoup
from selectolax.parser import HTMLParser
from price_parser import Price
import extruct

from .base_scraper import BaseScraper, ScrapingResult
from .ecommerce_detector import EcommerceDetector
from .data_normalizer import DataNormalizer

logger = logging.getLogger(__name__)


class ProductScraper(BaseScraper):
    """Specialized scraper for extracting product information"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ecommerce_detector = EcommerceDetector()
        self.data_normalizer = DataNormalizer()
    
    async def parse_content(self, soup: BeautifulSoup, tree: HTMLParser, url: str) -> Dict[str, Any]:
        """Parse product content from HTML"""
        
        # Detect e-commerce platform
        platform_info = self.ecommerce_detector.detect_platform(soup, url)
        
        # Check if this is a product page
        product_check = self.ecommerce_detector.is_product_page(soup, url)
        
        if not product_check["is_product"]:
            # Try to extract product listings instead
            return await self.parse_product_listing(soup, tree, url, platform_info)
        
        # Extract product data
        product_data = await self.extract_product_data(soup, tree, url, platform_info)
        
        return {
            "type": "product",
            "platform": platform_info,
            "product": product_data,
            "url": url,
            "confidence": product_check["confidence"]
        }
    
    async def scrape(self, url: str, **kwargs) -> ScrapingResult:
        """Scrape product data from URL"""
        if not self.should_scrape_url(url):
            return ScrapingResult(
                url=url,
                success=False,
                error="URL already scraped or invalid",
                scraper_type=self.__class__.__name__
            )
        
        return await self.fetch_page(url, **kwargs)
    
    async def extract_product_data(self, soup: BeautifulSoup, tree: HTMLParser, 
                                 url: str, platform_info: Dict[str, Any]) -> Dict[str, Any]:
        """Extract detailed product information"""
        
        selectors = platform_info.get("selectors", {})
        product_data = {
            "name": None,
            "description": None,
            "short_description": None,
            "price": None,
            "original_price": None,
            "currency": None,
            "availability": None,
            "sku": None,
            "brand": None,
            "category": None,
            "images": [],
            "variants": [],
            "attributes": {},
            "reviews": {
                "count": 0,
                "average_rating": 0,
                "ratings": []
            },
            "shipping_info": {},
            "seller_info": {},
            "social_proof": []
        }
        
        # Extract structured data first (most reliable)
        structured_data = self.extract_structured_data(soup)
        if structured_data:
            product_data.update(self.parse_structured_product_data(structured_data))
        
        # Extract product name/title
        product_data["name"] = self.extract_product_name(soup, selectors)
        
        # Extract pricing information
        pricing = self.extract_pricing(soup, selectors)
        product_data.update(pricing)
        
        # Extract descriptions
        descriptions = self.extract_descriptions(soup, selectors)
        product_data.update(descriptions)
        
        # Extract images
        product_data["images"] = self.extract_product_images(soup, url, selectors)
        
        # Extract variants/options
        product_data["variants"] = self.extract_variants(soup, selectors)
        
        # Extract availability
        product_data["availability"] = self.extract_availability(soup, selectors)
        
        # Extract brand information
        product_data["brand"] = self.extract_brand(soup, selectors)
        
        # Extract category/breadcrumbs
        product_data["category"] = self.extract_category(soup)
        
        # Extract SKU/Product ID
        product_data["sku"] = self.extract_sku(soup, selectors)
        
        # Extract reviews/ratings
        product_data["reviews"] = self.extract_reviews(soup, selectors)
        
        # Extract additional attributes
        product_data["attributes"] = self.extract_attributes(soup, selectors)
        
        # Extract shipping information
        product_data["shipping_info"] = self.extract_shipping_info(soup)
        
        # Extract seller information
        product_data["seller_info"] = self.extract_seller_info(soup)
        
        # Extract social proof elements
        product_data["social_proof"] = self.extract_social_proof(soup)
        
        # Normalize the data
        return self.data_normalizer.normalize_product_data(product_data)
    
    def extract_structured_data(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract JSON-LD structured data"""
        structured_data = []
        
        # JSON-LD
        json_ld_scripts = soup.find_all("script", type="application/ld+json")
        for script in json_ld_scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, list):
                    structured_data.extend(data)
                else:
                    structured_data.append(data)
            except (json.JSONDecodeError, TypeError):
                continue
        
        # Microdata and RDFa using extruct
        try:
            html_content = str(soup)
            extracted = extruct.extract(html_content)
            
            if extracted.get("json-ld"):
                structured_data.extend(extracted["json-ld"])
            
            if extracted.get("microdata"):
                structured_data.extend(extracted["microdata"])
                
        except Exception as e:
            logger.debug(f"Extruct extraction failed: {e}")
        
        return structured_data
    
    def parse_structured_product_data(self, structured_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Parse product data from structured data"""
        product_info = {}
        
        for data in structured_data:
            if not isinstance(data, dict):
                continue
            
            data_type = data.get("@type", "").lower()
            if "product" in data_type:
                # Product schema
                if data.get("name"):
                    product_info["name"] = data["name"]
                
                if data.get("description"):
                    product_info["description"] = data["description"]
                
                if data.get("brand"):
                    brand = data["brand"]
                    if isinstance(brand, dict):
                        product_info["brand"] = brand.get("name", "")
                    else:
                        product_info["brand"] = str(brand)
                
                if data.get("sku"):
                    product_info["sku"] = data["sku"]
                
                # Offers/pricing
                offers = data.get("offers", [])
                if isinstance(offers, dict):
                    offers = [offers]
                
                for offer in offers:
                    if isinstance(offer, dict):
                        if offer.get("price"):
                            product_info["price"] = offer["price"]
                        if offer.get("priceCurrency"):
                            product_info["currency"] = offer["priceCurrency"]
                        if offer.get("availability"):
                            product_info["availability"] = offer["availability"]
                
                # Images
                if data.get("image"):
                    images = data["image"]
                    if isinstance(images, str):
                        images = [images]
                    product_info["structured_images"] = images
                
                # Reviews/ratings
                if data.get("aggregateRating"):
                    rating = data["aggregateRating"]
                    product_info["aggregate_rating"] = {
                        "value": rating.get("ratingValue"),
                        "count": rating.get("reviewCount"),
                        "best": rating.get("bestRating"),
                        "worst": rating.get("worstRating")
                    }
        
        return product_info
    
    def extract_product_name(self, soup: BeautifulSoup, selectors: Dict[str, List[str]]) -> Optional[str]:
        """Extract product name/title"""
        
        title_selectors = selectors.get("title", [
            "h1", ".product-title", ".product-name", ".title",
            "[data-product-title]", ".product__title"
        ])
        
        for selector in title_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(strip=True)
                if text and len(text) > 5:  # Reasonable product name length
                    return text
        
        # Fallback to page title
        title_tag = soup.find("title")
        if title_tag:
            return title_tag.get_text(strip=True)
        
        return None
    
    def extract_pricing(self, soup: BeautifulSoup, selectors: Dict[str, List[str]]) -> Dict[str, Any]:
        """Extract pricing information"""
        
        pricing = {
            "price": None,
            "original_price": None,
            "currency": None,
            "price_range": None,
            "sale_price": None,
            "discount_percentage": None
        }
        
        price_selectors = selectors.get("price", [
            ".price", ".product-price", "[data-price]",
            ".cost", ".amount", ".price-current"
        ])
        
        prices_found = []
        
        for selector in price_selectors:
            elements = soup.select(selector)
            for element in elements:
                price_text = element.get_text(strip=True)
                if price_text:
                    # Parse price using price-parser
                    try:
                        parsed_price = Price.fromstring(price_text)
                        if parsed_price.amount:
                            prices_found.append({
                                "amount": float(parsed_price.amount),
                                "currency": parsed_price.currency,
                                "original_text": price_text,
                                "element_class": element.get("class", [])
                            })
                    except (ValueError, InvalidOperation):
                        continue
        
        if prices_found:
            # Sort prices to identify current vs original price
            prices_found.sort(key=lambda x: x["amount"])
            
            # Determine current price (usually the first/lowest in sale scenarios)
            current_price = prices_found[0]
            pricing["price"] = current_price["amount"]
            pricing["currency"] = current_price["currency"]
            
            # If multiple prices, higher one might be original price
            if len(prices_found) > 1:
                for price_info in prices_found[1:]:
                    # Check if it's marked as original/was price
                    classes = " ".join(price_info.get("element_class", []))
                    if any(term in classes.lower() for term in ["original", "was", "regular", "list"]):
                        pricing["original_price"] = price_info["amount"]
                        break
                
                # Calculate discount if we have both prices
                if pricing["original_price"] and pricing["original_price"] > pricing["price"]:
                    discount = ((pricing["original_price"] - pricing["price"]) / pricing["original_price"]) * 100
                    pricing["discount_percentage"] = round(discount, 2)
        
        return pricing
    
    def extract_descriptions(self, soup: BeautifulSoup, selectors: Dict[str, List[str]]) -> Dict[str, str]:
        """Extract product descriptions"""
        
        descriptions = {
            "description": None,
            "short_description": None
        }
        
        # Long description
        desc_selectors = selectors.get("description", [
            ".product-description", ".description", ".product-details",
            ".product__description", "[data-description]"
        ])
        
        for selector in desc_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(strip=True, separator=" ")
                if text and len(text) > 20:
                    descriptions["description"] = text
                    break
            if descriptions["description"]:
                break
        
        # Short description (usually first paragraph or summary)
        short_desc_selectors = [
            ".short-description", ".summary", ".product-summary",
            ".excerpt", ".product-excerpt"
        ]
        
        for selector in short_desc_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(strip=True)
                if text and len(text) < 500:  # Keep it short
                    descriptions["short_description"] = text
                    break
            if descriptions["short_description"]:
                break
        
        # If no short description found, extract first paragraph from long description
        if not descriptions["short_description"] and descriptions["description"]:
            first_paragraph = descriptions["description"].split("\n")[0]
            if len(first_paragraph) < 300:
                descriptions["short_description"] = first_paragraph
        
        return descriptions
    
    def extract_product_images(self, soup: BeautifulSoup, base_url: str, 
                             selectors: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        """Extract product images"""
        
        images = []
        image_selectors = selectors.get("images", [
            ".product-image img", ".product-gallery img", ".gallery img",
            ".product__media img", ".product-photos img"
        ])
        
        for selector in image_selectors:
            elements = soup.select(selector)
            for img in elements:
                src = img.get("src") or img.get("data-src") or img.get("data-lazy")
                if src:
                    full_url = self.normalize_url(src, base_url)
                    
                    image_info = {
                        "url": full_url,
                        "alt": img.get("alt", ""),
                        "title": img.get("title", ""),
                        "width": img.get("width"),
                        "height": img.get("height"),
                        "is_main": "main" in (img.get("class", []) or [])
                    }
                    
                    # Extract additional image sizes from srcset
                    srcset = img.get("srcset")
                    if srcset:
                        image_info["srcset"] = srcset
                        image_info["sizes"] = img.get("sizes", "")
                    
                    images.append(image_info)
        
        # Remove duplicates based on URL
        seen_urls = set()
        unique_images = []
        for img in images:
            if img["url"] not in seen_urls:
                seen_urls.add(img["url"])
                unique_images.append(img)
        
        return unique_images[:20]  # Limit to 20 images
    
    def extract_variants(self, soup: BeautifulSoup, selectors: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        """Extract product variants/options"""
        
        variants = []
        variant_selectors = selectors.get("variants", [
            ".variants", ".options", ".product-options",
            ".attributes", "[data-variant]"
        ])
        
        for selector in variant_selectors:
            variant_containers = soup.select(selector)
            
            for container in variant_containers:
                # Extract select dropdowns
                selects = container.find_all("select")
                for select in selects:
                    variant_name = (select.get("name") or 
                                  select.find_previous("label", {"for": select.get("id")}) or
                                  "").strip()
                    
                    options = []
                    for option in select.find_all("option"):
                        if option.get("value"):
                            options.append({
                                "value": option["value"],
                                "text": option.get_text(strip=True),
                                "available": not option.has_attr("disabled")
                            })
                    
                    if options:
                        variants.append({
                            "name": variant_name,
                            "type": "select",
                            "options": options
                        })
                
                # Extract radio buttons or checkboxes
                inputs = container.find_all("input", type=["radio", "checkbox"])
                current_variant = None
                options = []
                
                for inp in inputs:
                    name = inp.get("name", "")
                    if current_variant != name and options:
                        # Save previous variant
                        variants.append({
                            "name": current_variant,
                            "type": "radio" if inp.get("type") == "radio" else "checkbox",
                            "options": options
                        })
                        options = []
                    
                    current_variant = name
                    label = inp.find_next("label") or inp.find_previous("label")
                    label_text = label.get_text(strip=True) if label else inp.get("value", "")
                    
                    options.append({
                        "value": inp.get("value", ""),
                        "text": label_text,
                        "available": not inp.has_attr("disabled")
                    })
                
                # Add last variant
                if current_variant and options:
                    variants.append({
                        "name": current_variant,
                        "type": "radio",
                        "options": options
                    })
        
        return variants
    
    def extract_availability(self, soup: BeautifulSoup, selectors: Dict[str, List[str]]) -> Optional[str]:
        """Extract product availability status"""
        
        availability_selectors = selectors.get("availability", [
            ".stock", ".availability", ".product-availability",
            "[data-availability]", ".in-stock", ".out-of-stock"
        ])
        
        for selector in availability_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(strip=True).lower()
                
                # Check common availability indicators
                if any(term in text for term in ["in stock", "available", "ready to ship"]):
                    return "in_stock"
                elif any(term in text for term in ["out of stock", "sold out", "unavailable"]):
                    return "out_of_stock"
                elif any(term in text for term in ["pre-order", "backorder", "coming soon"]):
                    return "pre_order"
                elif "limited" in text:
                    return "limited_stock"
        
        # Check for add to cart button availability
        cart_buttons = soup.select(".add-to-cart, [data-add-to-cart], .buy-now")
        for button in cart_buttons:
            if button.has_attr("disabled") or "disabled" in button.get("class", []):
                return "out_of_stock"
        
        # Default to available if we found cart buttons
        if cart_buttons:
            return "in_stock"
        
        return "unknown"
    
    def extract_brand(self, soup: BeautifulSoup, selectors: Dict[str, List[str]]) -> Optional[str]:
        """Extract brand name"""
        
        # Try common brand selectors
        brand_selectors = [
            ".brand", ".brand-name", "[data-brand]",
            ".manufacturer", ".vendor"
        ]
        
        for selector in brand_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(strip=True)
                if text and len(text) < 100:  # Reasonable brand name length
                    return text
        
        # Check breadcrumbs for brand
        breadcrumb_links = soup.select(".breadcrumb a, .breadcrumbs a")
        if len(breadcrumb_links) > 1:
            # Usually brand is second item after "Home"
            potential_brand = breadcrumb_links[1].get_text(strip=True)
            if potential_brand.lower() not in ["products", "shop", "store"]:
                return potential_brand
        
        return None
    
    def extract_category(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract product category from breadcrumbs or navigation"""
        
        categories = []
        
        # Extract from breadcrumbs
        breadcrumb_selectors = [
            ".breadcrumb", ".breadcrumbs", ".navigation-path",
            "[data-breadcrumb]"
        ]
        
        for selector in breadcrumb_selectors:
            breadcrumb = soup.select_one(selector)
            if breadcrumb:
                links = breadcrumb.find_all("a")
                for link in links:
                    text = link.get_text(strip=True)
                    if text.lower() not in ["home", "shop", "store"]:
                        categories.append(text)
        
        # Return the deepest category (last one) or concatenate hierarchy
        if categories:
            return " > ".join(categories)
        
        return None
    
    def extract_sku(self, soup: BeautifulSoup, selectors: Dict[str, List[str]]) -> Optional[str]:
        """Extract SKU or product ID"""
        
        # Try common SKU selectors
        sku_selectors = [
            "[data-sku]", ".sku", ".product-id", ".item-number",
            "[data-product-id]", ".model-number"
        ]
        
        for selector in sku_selectors:
            element = soup.select_one(selector)
            if element:
                # Try data attribute first
                sku = element.get("data-sku") or element.get("data-product-id")
                if sku:
                    return sku
                
                # Try text content
                text = element.get_text(strip=True)
                if text and len(text) < 50:  # Reasonable SKU length
                    return text
        
        # Try to find SKU in text patterns
        text_content = soup.get_text()
        sku_patterns = [
            r"SKU[:\s]+([A-Z0-9\-_]+)",
            r"Product ID[:\s]+([A-Z0-9\-_]+)",
            r"Item #[:\s]+([A-Z0-9\-_]+)",
            r"Model[:\s]+([A-Z0-9\-_]+)"
        ]
        
        for pattern in sku_patterns:
            match = re.search(pattern, text_content, re.I)
            if match:
                return match.group(1)
        
        return None
    
    def extract_reviews(self, soup: BeautifulSoup, selectors: Dict[str, List[str]]) -> Dict[str, Any]:
        """Extract reviews and ratings"""
        
        reviews_data = {
            "count": 0,
            "average_rating": 0,
            "ratings": [],
            "review_highlights": []
        }
        
        # Extract star ratings
        rating_selectors = [
            ".rating", ".stars", ".star-rating", "[data-rating]"
        ]
        
        for selector in rating_selectors:
            elements = soup.select(selector)
            for element in elements:
                # Try to extract rating from classes or data attributes
                rating_value = (element.get("data-rating") or 
                              element.get("data-stars") or
                              element.get("title"))
                
                if rating_value:
                    try:
                        rating = float(rating_value)
                        if 0 <= rating <= 5:
                            reviews_data["average_rating"] = rating
                            break
                    except ValueError:
                        pass
                
                # Try to count filled stars
                filled_stars = element.select(".star-filled, .filled, .active")
                if filled_stars:
                    reviews_data["average_rating"] = len(filled_stars)
        
        # Extract review count
        count_selectors = [
            ".review-count", ".reviews-count", "[data-review-count]"
        ]
        
        for selector in count_selectors:
            element = soup.select_one(selector)
            if element:
                count_text = element.get_text(strip=True)
                count_match = re.search(r"(\d+)", count_text)
                if count_match:
                    reviews_data["count"] = int(count_match.group(1))
                    break
        
        return reviews_data
    
    def extract_attributes(self, soup: BeautifulSoup, selectors: Dict[str, List[str]]) -> Dict[str, Any]:
        """Extract product attributes/specifications"""
        
        attributes = {}
        
        # Try to find specification tables
        spec_tables = soup.select("table.specs, .specifications table, .product-specs table")
        for table in spec_tables:
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all(["td", "th"])
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True)
                    value = cells[1].get_text(strip=True)
                    if key and value:
                        attributes[key] = value
        
        # Try to find attribute lists
        attr_lists = soup.select(".attributes dl, .specs dl, .product-attributes dl")
        for dl in attr_lists:
            terms = dl.find_all("dt")
            definitions = dl.find_all("dd")
            
            for term, definition in zip(terms, definitions):
                key = term.get_text(strip=True)
                value = definition.get_text(strip=True)
                if key and value:
                    attributes[key] = value
        
        return attributes
    
    def extract_shipping_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract shipping information"""
        
        shipping_info = {}
        
        shipping_selectors = [
            ".shipping-info", ".delivery-info", ".shipping-details"
        ]
        
        for selector in shipping_selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                shipping_info["description"] = text
                
                # Try to extract free shipping info
                if "free" in text.lower():
                    shipping_info["free_shipping"] = True
                
                # Try to extract delivery time
                time_patterns = [
                    r"(\d+)-?(\d+)?\s*(day|week|month)s?",
                    r"within\s+(\d+)\s*(day|week|month)s?",
                    r"(same day|next day|overnight)"
                ]
                
                for pattern in time_patterns:
                    match = re.search(pattern, text.lower())
                    if match:
                        shipping_info["delivery_time"] = match.group(0)
                        break
                
                break
        
        return shipping_info
    
    def extract_seller_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract seller/vendor information"""
        
        seller_info = {}
        
        seller_selectors = [
            ".seller", ".vendor", ".merchant", ".sold-by"
        ]
        
        for selector in seller_selectors:
            element = soup.select_one(selector)
            if element:
                seller_name = element.get_text(strip=True)
                if seller_name:
                    seller_info["name"] = seller_name
                    
                    # Try to find seller rating
                    rating_element = element.find_next(class_=["rating", "stars"])
                    if rating_element:
                        seller_info["rating"] = rating_element.get_text(strip=True)
                    
                    break
        
        return seller_info
    
    def extract_social_proof(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract social proof elements"""
        
        social_proof = []
        
        # Recently viewed/purchased indicators
        social_indicators = soup.select(".social-proof, .recently-viewed, .other-customers")
        for indicator in social_indicators:
            text = indicator.get_text(strip=True)
            if text:
                social_proof.append({
                    "type": "activity",
                    "text": text
                })
        
        # Trust badges/certifications
        trust_badges = soup.select(".trust-badge, .certification, .security-badge")
        for badge in trust_badges:
            alt_text = badge.get("alt", "")
            title = badge.get("title", "")
            text = alt_text or title or badge.get_text(strip=True)
            
            if text:
                social_proof.append({
                    "type": "trust_badge",
                    "text": text
                })
        
        return social_proof
    
    async def parse_product_listing(self, soup: BeautifulSoup, tree: HTMLParser, 
                                  url: str, platform_info: Dict[str, Any]) -> Dict[str, Any]:
        """Parse product listing/category pages"""
        
        listing_data = {
            "type": "product_listing",
            "platform": platform_info,
            "products": [],
            "pagination": {},
            "filters": [],
            "total_products": 0
        }
        
        # Detect listing patterns
        patterns = self.ecommerce_detector.detect_product_listing_patterns(soup)
        
        # Extract individual products from listing
        for selector in patterns.get("product_items", []):
            product_elements = soup.select(selector)
            
            for element in product_elements[:20]:  # Limit to 20 products per page
                product = self.extract_listing_product(element, url)
                if product:
                    listing_data["products"].append(product)
        
        # Extract pagination info
        pagination_elements = soup.select(".pagination a, .pager a, .page-numbers a")
        if pagination_elements:
            listing_data["pagination"] = {
                "has_pagination": True,
                "pages": len(pagination_elements),
                "current_page": self.extract_current_page(soup)
            }
        
        listing_data["total_products"] = len(listing_data["products"])
        
        return listing_data
    
    def extract_listing_product(self, element: BeautifulSoup, base_url: str) -> Optional[Dict[str, Any]]:
        """Extract product info from listing item"""
        
        product = {}
        
        # Product link
        link = element.find("a", href=True)
        if link:
            product["url"] = self.normalize_url(link["href"], base_url)
        
        # Product name
        name_selectors = ["h2", "h3", ".product-name", ".title"]
        for selector in name_selectors:
            name_element = element.select_one(selector)
            if name_element:
                product["name"] = name_element.get_text(strip=True)
                break
        
        # Price
        price_element = element.select_one(".price, .cost, .amount")
        if price_element:
            price_text = price_element.get_text(strip=True)
            try:
                parsed_price = Price.fromstring(price_text)
                if parsed_price.amount:
                    product["price"] = float(parsed_price.amount)
                    product["currency"] = parsed_price.currency
            except:
                pass
        
        # Image
        img = element.find("img", src=True)
        if img:
            product["image"] = self.normalize_url(img["src"], base_url)
            product["image_alt"] = img.get("alt", "")
        
        # Basic validation
        if not product.get("name") or not product.get("url"):
            return None
        
        return product
    
    def extract_current_page(self, soup: BeautifulSoup) -> int:
        """Extract current page number from pagination"""
        
        current_selectors = [
            ".pagination .current", ".pager .active", 
            ".page-numbers .current", "[aria-current='page']"
        ]
        
        for selector in current_selectors:
            element = soup.select_one(selector)
            if element:
                page_text = element.get_text(strip=True)
                try:
                    return int(page_text)
                except ValueError:
                    pass
        
        return 1  # Default to page 1