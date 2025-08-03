"""
Data normalization and cleaning utilities for scraped content.
"""

import re
import html
from typing import Any, Dict, List, Optional, Union
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse
import logging

from price_parser import Price

logger = logging.getLogger(__name__)


class DataNormalizer:
    """Normalize and clean scraped data"""
    
    def __init__(self):
        self.currency_symbols = {
            "$": "USD",
            "€": "EUR", 
            "£": "GBP",
            "¥": "JPY",
            "₹": "INR",
            "C$": "CAD",
            "A$": "AUD",
            "₽": "RUB",
            "¢": "USD",  # cents
            "p": "GBP",  # pence
        }
        
        self.size_units = ["XS", "S", "M", "L", "XL", "XXL", "XXXL"]
        self.color_keywords = [
            "black", "white", "red", "blue", "green", "yellow", "purple",
            "pink", "orange", "brown", "gray", "grey", "navy", "beige",
            "tan", "cream", "gold", "silver", "rose", "coral", "mint"
        ]
    
    def normalize_product_data(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize complete product data"""
        
        normalized = product_data.copy()
        
        # Normalize text fields
        text_fields = ["name", "description", "short_description", "brand", "category"]
        for field in text_fields:
            if normalized.get(field):
                normalized[field] = self.normalize_text(normalized[field])
        
        # Normalize pricing
        if normalized.get("price"):
            normalized["price"] = self.normalize_price(normalized["price"])
        
        if normalized.get("original_price"):
            normalized["original_price"] = self.normalize_price(normalized["original_price"])
        
        # Normalize currency
        if normalized.get("currency"):
            normalized["currency"] = self.normalize_currency(normalized["currency"])
        
        # Normalize availability
        if normalized.get("availability"):
            normalized["availability"] = self.normalize_availability(normalized["availability"])
        
        # Normalize images
        if normalized.get("images"):
            normalized["images"] = [self.normalize_image_data(img) for img in normalized["images"]]
        
        # Normalize variants
        if normalized.get("variants"):
            normalized["variants"] = [self.normalize_variant(variant) for variant in normalized["variants"]]
        
        # Normalize attributes
        if normalized.get("attributes"):
            normalized["attributes"] = self.normalize_attributes(normalized["attributes"])
        
        # Extract and normalize key product features
        normalized["features"] = self.extract_features(normalized)
        
        # Generate product tags
        normalized["tags"] = self.generate_tags(normalized)
        
        # Calculate confidence score
        normalized["data_quality_score"] = self.calculate_quality_score(normalized)
        
        return normalized
    
    def normalize_text(self, text: str) -> str:
        """Normalize text content"""
        if not text:
            return ""
        
        # Decode HTML entities
        text = html.unescape(text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove common unwanted characters
        text = re.sub(r'[^\w\s\-.,!?()&/]', '', text)
        
        # Limit length for sanity
        if len(text) > 5000:
            text = text[:5000] + "..."
        
        return text
    
    def normalize_price(self, price: Union[str, float, int]) -> Optional[float]:
        """Normalize price to float"""
        if price is None:
            return None
        
        if isinstance(price, (int, float)):
            return float(price) if price > 0 else None
        
        if isinstance(price, str):
            try:
                # Use price-parser for robust parsing
                parsed = Price.fromstring(price)
                if parsed.amount and parsed.amount > 0:
                    return float(parsed.amount)
            except (ValueError, AttributeError, TypeError) as e:
                logger.debug(f"Price parser failed for '{price}': {e}")
                pass
            
            # Fallback manual parsing
            try:
                # Remove currency symbols and extract numbers
                clean_price = re.sub(r'[^\d.,]', '', price)
                clean_price = clean_price.replace(',', '')
                
                if clean_price:
                    return float(clean_price)
            except (ValueError, InvalidOperation):
                pass
        
        return None
    
    def normalize_currency(self, currency: str) -> str:
        """Normalize currency code"""
        if not currency:
            return "USD"  # Default
        
        currency = currency.strip().upper()
        
        # Handle currency symbols
        if currency in self.currency_symbols:
            return self.currency_symbols[currency]
        
        # Handle common currency codes
        if len(currency) == 3 and currency.isalpha():
            return currency
        
        # Handle currency names
        currency_names = {
            "DOLLAR": "USD",
            "DOLLARS": "USD", 
            "EURO": "EUR",
            "EUROS": "EUR",
            "POUND": "GBP",
            "POUNDS": "GBP",
            "YEN": "JPY"
        }
        
        return currency_names.get(currency, "USD")
    
    def normalize_availability(self, availability: str) -> str:
        """Normalize availability status"""
        if not availability:
            return "unknown"
        
        availability = availability.lower().strip()
        
        # Map various availability statuses
        if any(term in availability for term in ["in stock", "available", "ready", "ships"]):
            return "in_stock"
        elif any(term in availability for term in ["out of stock", "sold out", "unavailable"]):
            return "out_of_stock"
        elif any(term in availability for term in ["pre-order", "preorder", "coming soon"]):
            return "pre_order"
        elif any(term in availability for term in ["backorder", "back order"]):
            return "backorder"
        elif any(term in availability for term in ["limited", "low stock", "few left"]):
            return "limited_stock"
        elif any(term in availability for term in ["discontinued", "no longer"]):
            return "discontinued"
        
        return "unknown"
    
    def normalize_image_data(self, image_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize image data"""
        if not isinstance(image_data, dict):
            return {}
        
        normalized = image_data.copy()
        
        # Normalize URL
        if normalized.get("url"):
            normalized["url"] = self.normalize_url(normalized["url"])
        
        # Normalize alt text
        if normalized.get("alt"):
            normalized["alt"] = self.normalize_text(normalized["alt"])
        
        # Extract image type from alt text or URL
        normalized["type"] = self.classify_image_type(normalized)
        
        # Validate dimensions
        for dim in ["width", "height"]:
            if normalized.get(dim):
                try:
                    normalized[dim] = int(str(normalized[dim]).replace("px", ""))
                except (ValueError, TypeError):
                    normalized[dim] = None
        
        return normalized
    
    def normalize_variant(self, variant: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize variant data"""
        if not isinstance(variant, dict):
            return {}
        
        normalized = variant.copy()
        
        # Normalize variant name
        if normalized.get("name"):
            normalized["name"] = self.normalize_text(normalized["name"])
            normalized["normalized_name"] = self.normalize_variant_name(normalized["name"])
        
        # Normalize options
        if normalized.get("options"):
            normalized["options"] = [
                self.normalize_variant_option(option) 
                for option in normalized["options"]
            ]
        
        return normalized
    
    def normalize_variant_name(self, name: str) -> str:
        """Normalize variant name to standard categories"""
        if not name:
            return "other"
        
        name_lower = name.lower()
        
        # Map to standard variant types
        if any(term in name_lower for term in ["color", "colour"]):
            return "color"
        elif any(term in name_lower for term in ["size"]):
            return "size"
        elif any(term in name_lower for term in ["material", "fabric"]):
            return "material"
        elif any(term in name_lower for term in ["style", "type"]):
            return "style"
        elif any(term in name_lower for term in ["capacity", "storage", "memory"]):
            return "capacity"
        elif any(term in name_lower for term in ["length", "height", "width"]):
            return "dimensions"
        
        return "other"
    
    def normalize_variant_option(self, option: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize variant option"""
        if not isinstance(option, dict):
            return {}
        
        normalized = option.copy()
        
        # Normalize text fields
        for field in ["value", "text"]:
            if normalized.get(field):
                normalized[field] = self.normalize_text(normalized[field])
        
        # Extract normalized value based on type
        text = normalized.get("text", normalized.get("value", ""))
        normalized["normalized_value"] = self.normalize_option_value(text)
        
        return normalized
    
    def normalize_option_value(self, value: str) -> str:
        """Normalize option value (size, color, etc.)"""
        if not value:
            return ""
        
        value = value.strip()
        
        # Normalize sizes
        value_upper = value.upper()
        if value_upper in self.size_units:
            return value_upper
        
        # Normalize colors
        value_lower = value.lower()
        for color in self.color_keywords:
            if color in value_lower:
                return color.title()
        
        # Normalize numeric values (capacities, dimensions)
        numeric_match = re.search(r'(\d+(?:\.\d+)?)\s*([a-zA-Z]*)', value)
        if numeric_match:
            number, unit = numeric_match.groups()
            if unit.lower() in ["gb", "tb", "mb", "kg", "lb", "oz", "ml", "l"]:
                return f"{number}{unit.lower()}"
        
        return value
    
    def normalize_attributes(self, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize product attributes"""
        if not isinstance(attributes, dict):
            return {}
        
        normalized = {}
        
        for key, value in attributes.items():
            # Normalize key
            normalized_key = self.normalize_attribute_key(key)
            
            # Normalize value
            normalized_value = self.normalize_attribute_value(value)
            
            if normalized_key and normalized_value:
                normalized[normalized_key] = normalized_value
        
        return normalized
    
    def normalize_attribute_key(self, key: str) -> str:
        """Normalize attribute key to standard format"""
        if not key:
            return ""
        
        # Convert to lowercase and replace separators
        key = re.sub(r'[^\w\s]', '', key.lower())
        key = re.sub(r'\s+', '_', key.strip())
        
        # Map to standard attribute names
        key_mappings = {
            "brand_name": "brand",
            "manufacturer": "brand",
            "model_number": "model",
            "model_name": "model",
            "product_weight": "weight",
            "item_weight": "weight",
            "product_dimensions": "dimensions",
            "item_dimensions": "dimensions",
            "package_dimensions": "package_size",
            "color_name": "color",
            "size_name": "size",
            "material_type": "material",
            "fabric_type": "material"
        }
        
        return key_mappings.get(key, key)
    
    def normalize_attribute_value(self, value: Union[str, int, float]) -> str:
        """Normalize attribute value"""
        if value is None:
            return ""
        
        value_str = str(value).strip()
        
        if not value_str:
            return ""
        
        # Limit length
        if len(value_str) > 200:
            value_str = value_str[:200] + "..."
        
        return self.normalize_text(value_str)
    
    def normalize_url(self, url: str) -> str:
        """Normalize URL"""
        if not url:
            return ""
        
        # Remove query parameters for cleaner URLs (keep essential ones)
        parsed = urlparse(url)
        
        # Keep only essential query parameters
        essential_params = ["v", "id", "variant", "color", "size"]
        
        if parsed.query:
            # For now, keep all query params to avoid breaking functionality
            # In production, you might want to filter these
            pass
        
        return url.strip()
    
    def classify_image_type(self, image_data: Dict[str, Any]) -> str:
        """Classify image type based on context"""
        alt_text = image_data.get("alt", "").lower()
        url = image_data.get("url", "").lower()
        
        if any(term in alt_text for term in ["main", "primary", "hero"]):
            return "main"
        elif any(term in alt_text for term in ["gallery", "additional", "alternate"]):
            return "gallery"
        elif any(term in alt_text for term in ["thumbnail", "thumb"]):
            return "thumbnail"
        elif any(term in alt_text for term in ["zoom", "detail", "closeup"]):
            return "detail"
        elif any(term in url for term in ["thumb", "small"]):
            return "thumbnail"
        elif any(term in url for term in ["large", "zoom"]):
            return "large"
        
        return "product"
    
    def extract_features(self, product_data: Dict[str, Any]) -> List[str]:
        """Extract key product features"""
        features = []
        
        # Extract from description
        description = product_data.get("description", "")
        if description:
            # Look for bullet points or feature lists
            feature_patterns = [
                r"• (.+)",
                r"- (.+)",
                r"\* (.+)",
                r"✓ (.+)"
            ]
            
            for pattern in feature_patterns:
                matches = re.findall(pattern, description)
                features.extend([match.strip() for match in matches[:5]])  # Limit to 5
        
        # Extract from attributes
        attributes = product_data.get("attributes", {})
        for key, value in attributes.items():
            if key.lower() in ["features", "highlights", "benefits"]:
                if isinstance(value, str):
                    # Split on common separators
                    feature_items = re.split(r'[,;|]', value)
                    features.extend([item.strip() for item in feature_items if item.strip()])
        
        # Extract from structured data
        if product_data.get("structured_data"):
            # Implementation would extract features from structured data
            pass
        
        # Clean and limit features
        clean_features = []
        for feature in features:
            if len(feature) > 10 and len(feature) < 100:  # Reasonable feature length
                clean_features.append(self.normalize_text(feature))
        
        return clean_features[:10]  # Limit to 10 features
    
    def generate_tags(self, product_data: Dict[str, Any]) -> List[str]:
        """Generate tags for the product"""
        tags = set()
        
        # Add brand as tag
        if product_data.get("brand"):
            tags.add(product_data["brand"].lower())
        
        # Add category tags
        category = product_data.get("category", "")
        if category:
            category_parts = category.split(" > ")
            tags.update([part.strip().lower() for part in category_parts])
        
        # Add color tags from variants
        variants = product_data.get("variants", [])
        for variant in variants:
            if variant.get("normalized_name") == "color":
                for option in variant.get("options", []):
                    color = option.get("normalized_value", "")
                    if color:
                        tags.add(color.lower())
        
        # Add material tags from attributes
        attributes = product_data.get("attributes", {})
        if "material" in attributes:
            material = attributes["material"].lower()
            tags.add(material)
        
        # Add price range tags
        price = product_data.get("price")
        if price:
            if price < 25:
                tags.add("budget")
            elif price < 100:
                tags.add("mid-range")
            else:
                tags.add("premium")
        
        # Add availability tag
        availability = product_data.get("availability")
        if availability:
            tags.add(availability)
        
        return list(tags)[:20]  # Limit to 20 tags
    
    def calculate_quality_score(self, product_data: Dict[str, Any]) -> float:
        """Calculate data quality score (0-1)"""
        score = 0.0
        max_score = 0.0
        
        # Required fields (higher weight)
        required_fields = {
            "name": 0.2,
            "price": 0.15,
            "description": 0.15
        }
        
        for field, weight in required_fields.items():
            max_score += weight
            if product_data.get(field):
                score += weight
        
        # Optional but valuable fields
        optional_fields = {
            "brand": 0.1,
            "images": 0.1,
            "category": 0.05,
            "availability": 0.05,
            "variants": 0.05,
            "attributes": 0.05,
            "reviews": 0.05,
            "sku": 0.05
        }
        
        for field, weight in optional_fields.items():
            max_score += weight
            value = product_data.get(field)
            if value:
                if isinstance(value, (list, dict)) and len(value) > 0:
                    score += weight
                elif isinstance(value, str) and value.strip():
                    score += weight
                elif isinstance(value, (int, float)) and value > 0:
                    score += weight
        
        # Quality bonuses
        quality_bonuses = {
            "has_multiple_images": 0.05,
            "has_detailed_description": 0.05,
            "has_structured_data": 0.05
        }
        
        for bonus, weight in quality_bonuses.items():
            max_score += weight
            
            if bonus == "has_multiple_images":
                images = product_data.get("images", [])
                if len(images) > 1:
                    score += weight
            elif bonus == "has_detailed_description":
                description = product_data.get("description", "")
                if len(description) > 100:
                    score += weight
            elif bonus == "has_structured_data":
                if product_data.get("structured_data"):
                    score += weight
        
        return round(score / max_score, 2) if max_score > 0 else 0.0