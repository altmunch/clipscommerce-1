"""
AI Cache Management Service

Provides intelligent caching strategies for expensive AI operations,
including semantic caching, multi-level caching, and cache optimization.
"""

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union, Callable
import logging
from collections import defaultdict, OrderedDict
import pickle
import gzip

import numpy as np
from diskcache import Cache

from app.core.config import settings

logger = logging.getLogger(__name__)


class CacheStrategy(str, Enum):
    """Cache strategies"""
    EXACT_MATCH = "exact_match"
    SEMANTIC_SIMILARITY = "semantic_similarity"
    FUZZY_MATCH = "fuzzy_match"
    TEMPLATE_BASED = "template_based"
    PARAMETER_NORMALIZED = "parameter_normalized"


class CacheLevel(str, Enum):
    """Cache levels"""
    L1_MEMORY = "l1_memory"
    L2_DISK = "l2_disk"
    L3_DISTRIBUTED = "l3_distributed"


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    key: str
    value: Any
    strategy: CacheStrategy
    created_at: float
    last_accessed: float
    access_count: int
    cost_saved: float  # Estimated cost savings
    size_bytes: int
    ttl: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        if self.ttl is None:
            return False
        return time.time() > self.created_at + self.ttl
    
    def update_access(self):
        """Update access statistics"""
        self.last_accessed = time.time()
        self.access_count += 1
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "strategy": self.strategy,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
            "cost_saved": self.cost_saved,
            "size_bytes": self.size_bytes,
            "ttl": self.ttl,
            "metadata": self.metadata,
            "is_expired": self.is_expired()
        }


@dataclass
class CacheStats:
    """Cache performance statistics"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_size_bytes: int = 0
    total_cost_saved: float = 0.0
    
    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    @property
    def miss_rate(self) -> float:
        return 1.0 - self.hit_rate
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "hit_rate": self.hit_rate,
            "miss_rate": self.miss_rate,
            "total_size_bytes": self.total_size_bytes,
            "total_cost_saved": self.total_cost_saved
        }


class SemanticCache:
    """Semantic similarity-based caching"""
    
    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold
        self.embeddings_cache = {}
        self.embedding_service = None
    
    async def _get_embedding_service(self):
        """Get embedding service for semantic similarity"""
        if self.embedding_service is None:
            try:
                from app.services.ai.providers import get_embedding_service
                self.embedding_service = await get_embedding_service()
            except Exception as e:
                logger.error(f"Failed to initialize embedding service: {e}")
                return None
        return self.embedding_service
    
    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding for text"""
        # Check cache first
        text_hash = hashlib.md5(text.encode()).hexdigest()
        if text_hash in self.embeddings_cache:
            return self.embeddings_cache[text_hash]
        
        # Generate embedding
        embedding_service = await self._get_embedding_service()
        if not embedding_service:
            return None
        
        try:
            embeddings = await embedding_service.generate_embeddings([text])
            if embeddings:
                embedding = embeddings[0]
                self.embeddings_cache[text_hash] = embedding
                return embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
        
        return None
    
    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity between embeddings"""
        try:
            a = np.array(embedding1)
            b = np.array(embedding2)
            
            # Cosine similarity
            similarity = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
            return float(similarity)
        except Exception as e:
            logger.error(f"Failed to calculate similarity: {e}")
            return 0.0
    
    async def find_similar_entries(
        self,
        query_text: str,
        cached_entries: Dict[str, CacheEntry]
    ) -> List[Tuple[str, float, CacheEntry]]:
        """Find semantically similar cache entries"""
        
        query_embedding = await self.get_embedding(query_text)
        if not query_embedding:
            return []
        
        similar_entries = []
        
        for key, entry in cached_entries.items():
            # Get cached text from metadata
            cached_text = entry.metadata.get("original_text", "")
            if not cached_text:
                continue
            
            cached_embedding = await self.get_embedding(cached_text)
            if not cached_embedding:
                continue
            
            similarity = self.calculate_similarity(query_embedding, cached_embedding)
            
            if similarity >= self.similarity_threshold:
                similar_entries.append((key, similarity, entry))
        
        # Sort by similarity
        similar_entries.sort(key=lambda x: x[1], reverse=True)
        return similar_entries


class FuzzyMatcher:
    """Fuzzy matching for cache keys"""
    
    def __init__(self, threshold: float = 0.8):
        self.threshold = threshold
    
    def calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate string similarity using Levenshtein distance"""
        try:
            # Simple implementation - in production, use proper fuzzy matching library
            if str1 == str2:
                return 1.0
            
            # Normalize strings
            s1 = str1.lower().strip()
            s2 = str2.lower().strip()
            
            if not s1 or not s2:
                return 0.0
            
            # Calculate Levenshtein distance
            len1, len2 = len(s1), len(s2)
            
            # Create matrix
            matrix = [[0] * (len2 + 1) for _ in range(len1 + 1)]
            
            # Initialize first row and column
            for i in range(len1 + 1):
                matrix[i][0] = i
            for j in range(len2 + 1):
                matrix[0][j] = j
            
            # Fill matrix
            for i in range(1, len1 + 1):
                for j in range(1, len2 + 1):
                    if s1[i-1] == s2[j-1]:
                        cost = 0
                    else:
                        cost = 1
                    
                    matrix[i][j] = min(
                        matrix[i-1][j] + 1,      # deletion
                        matrix[i][j-1] + 1,      # insertion
                        matrix[i-1][j-1] + cost  # substitution
                    )
            
            # Calculate similarity
            distance = matrix[len1][len2]
            max_len = max(len1, len2)
            
            if max_len == 0:
                return 1.0
            
            similarity = 1.0 - (distance / max_len)
            return similarity
            
        except Exception as e:
            logger.error(f"Failed to calculate fuzzy similarity: {e}")
            return 0.0
    
    def find_similar_keys(self, query: str, keys: List[str]) -> List[Tuple[str, float]]:
        """Find similar keys using fuzzy matching"""
        
        similar_keys = []
        
        for key in keys:
            similarity = self.calculate_similarity(query, key)
            if similarity >= self.threshold:
                similar_keys.append((key, similarity))
        
        # Sort by similarity
        similar_keys.sort(key=lambda x: x[1], reverse=True)
        return similar_keys


class LRUCache:
    """Least Recently Used cache implementation"""
    
    def __init__(self, max_size: int):
        self.max_size = max_size
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.stats = CacheStats()
    
    def get(self, key: str) -> Optional[CacheEntry]:
        """Get item from cache"""
        if key in self.cache:
            entry = self.cache[key]
            
            # Check expiration
            if entry.is_expired():
                del self.cache[key]
                self.stats.misses += 1
                return None
            
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            entry.update_access()
            self.stats.hits += 1
            
            return entry
        
        self.stats.misses += 1
        return None
    
    def put(self, key: str, entry: CacheEntry):
        """Put item in cache"""
        if key in self.cache:
            # Update existing entry
            self.cache[key] = entry
            self.cache.move_to_end(key)
        else:
            # Add new entry
            if len(self.cache) >= self.max_size:
                # Remove least recently used
                oldest_key, oldest_entry = self.cache.popitem(last=False)
                self.stats.evictions += 1
                self.stats.total_size_bytes -= oldest_entry.size_bytes
            
            self.cache[key] = entry
            self.stats.total_size_bytes += entry.size_bytes
    
    def remove(self, key: str) -> bool:
        """Remove item from cache"""
        if key in self.cache:
            entry = self.cache.pop(key)
            self.stats.total_size_bytes -= entry.size_bytes
            return True
        return False
    
    def clear(self):
        """Clear all cache entries"""
        self.cache.clear()
        self.stats = CacheStats()
    
    def keys(self) -> List[str]:
        """Get all cache keys"""
        return list(self.cache.keys())
    
    def values(self) -> List[CacheEntry]:
        """Get all cache entries"""
        return list(self.cache.values())
    
    def items(self) -> List[Tuple[str, CacheEntry]]:
        """Get all cache items"""
        return list(self.cache.items())


class MultiLevelCache:
    """Multi-level caching system"""
    
    def __init__(self):
        # L1: In-memory LRU cache (fast, small)
        self.l1_cache = LRUCache(max_size=1000)
        
        # L2: Disk cache (slower, larger)
        self.l2_cache = Cache("/tmp/viralos_l2_cache", size_limit=2000000000)  # 2GB
        
        # L3: Would be distributed cache in production
        self.l3_cache = None
        
        self.semantic_cache = SemanticCache()
        self.fuzzy_matcher = FuzzyMatcher()
    
    def _serialize_value(self, value: Any) -> bytes:
        """Serialize value for storage"""
        try:
            # Compress for better storage efficiency
            serialized = pickle.dumps(value)
            compressed = gzip.compress(serialized)
            return compressed
        except Exception as e:
            logger.error(f"Failed to serialize value: {e}")
            return b""
    
    def _deserialize_value(self, data: bytes) -> Any:
        """Deserialize value from storage"""
        try:
            decompressed = gzip.decompress(data)
            value = pickle.loads(decompressed)
            return value
        except Exception as e:
            logger.error(f"Failed to deserialize value: {e}")
            return None
    
    def _calculate_entry_size(self, value: Any) -> int:
        """Calculate size of cache entry in bytes"""
        try:
            serialized = self._serialize_value(value)
            return len(serialized)
        except Exception:
            return 1024  # Default estimate
    
    def _generate_cache_key(
        self,
        service_name: str,
        operation: str,
        inputs: Dict[str, Any],
        strategy: CacheStrategy = CacheStrategy.EXACT_MATCH
    ) -> str:
        """Generate cache key based on inputs and strategy"""
        
        if strategy == CacheStrategy.EXACT_MATCH:
            # Hash all inputs exactly
            inputs_str = json.dumps(inputs, sort_keys=True, default=str)
            key_data = f"{service_name}:{operation}:{inputs_str}"
            
        elif strategy == CacheStrategy.PARAMETER_NORMALIZED:
            # Normalize parameters before hashing
            normalized_inputs = self._normalize_inputs(inputs)
            inputs_str = json.dumps(normalized_inputs, sort_keys=True, default=str)
            key_data = f"{service_name}:{operation}:{inputs_str}"
            
        elif strategy == CacheStrategy.TEMPLATE_BASED:
            # Use only key parameters
            key_params = self._extract_key_parameters(service_name, operation, inputs)
            inputs_str = json.dumps(key_params, sort_keys=True, default=str)
            key_data = f"{service_name}:{operation}:{inputs_str}"
            
        else:
            # Default to exact match
            inputs_str = json.dumps(inputs, sort_keys=True, default=str)
            key_data = f"{service_name}:{operation}:{inputs_str}"
        
        # Generate hash
        return hashlib.sha256(key_data.encode()).hexdigest()
    
    def _normalize_inputs(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize inputs for consistent caching"""
        normalized = {}
        
        for key, value in inputs.items():
            if isinstance(value, str):
                # Normalize text
                normalized[key] = value.strip().lower()
            elif isinstance(value, (int, float)):
                # Round numbers to reduce cache misses from tiny differences
                if isinstance(value, float):
                    normalized[key] = round(value, 4)
                else:
                    normalized[key] = value
            elif isinstance(value, list):
                # Sort lists for consistency
                try:
                    normalized[key] = sorted(value)
                except TypeError:
                    normalized[key] = value
            else:
                normalized[key] = value
        
        return normalized
    
    def _extract_key_parameters(
        self,
        service_name: str,
        operation: str,
        inputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract key parameters for template-based caching"""
        
        # Define key parameters for different operations
        key_param_map = {
            "viral_content": {
                "generate_viral_hooks": ["content_pillar", "platform", "target_audience"],
                "analyze_viral_potential": ["content", "platform"]
            },
            "brand_assimilation": {
                "analyze_brand_identity": ["brand_name", "website_content"],
                "extract_brand_voice": ["brand_content"]
            },
            "text_generation": {
                "generate": ["prompt", "model", "max_tokens", "temperature"]
            }
        }
        
        service_params = key_param_map.get(service_name, {})
        operation_params = service_params.get(operation, [])
        
        # Extract only key parameters
        key_inputs = {}
        for param in operation_params:
            if param in inputs:
                key_inputs[param] = inputs[param]
        
        # If no key parameters defined, use all inputs
        if not key_inputs:
            key_inputs = inputs
        
        return key_inputs
    
    async def get(
        self,
        service_name: str,
        operation: str,
        inputs: Dict[str, Any],
        strategy: CacheStrategy = CacheStrategy.EXACT_MATCH
    ) -> Optional[Any]:
        """Get value from multi-level cache"""
        
        # Try different strategies in order of preference
        strategies_to_try = [strategy]
        
        # Add fallback strategies
        if strategy != CacheStrategy.EXACT_MATCH:
            strategies_to_try.append(CacheStrategy.EXACT_MATCH)
        
        if strategy not in [CacheStrategy.SEMANTIC_SIMILARITY, CacheStrategy.FUZZY_MATCH]:
            strategies_to_try.extend([CacheStrategy.SEMANTIC_SIMILARITY, CacheStrategy.FUZZY_MATCH])
        
        for current_strategy in strategies_to_try:
            result = await self._get_with_strategy(service_name, operation, inputs, current_strategy)
            if result is not None:
                return result
        
        return None
    
    async def _get_with_strategy(
        self,
        service_name: str,
        operation: str,
        inputs: Dict[str, Any],
        strategy: CacheStrategy
    ) -> Optional[Any]:
        """Get value using specific strategy"""
        
        if strategy == CacheStrategy.SEMANTIC_SIMILARITY:
            return await self._get_semantic_match(service_name, operation, inputs)
        elif strategy == CacheStrategy.FUZZY_MATCH:
            return await self._get_fuzzy_match(service_name, operation, inputs)
        else:
            # Exact, normalized, or template-based matching
            cache_key = self._generate_cache_key(service_name, operation, inputs, strategy)
            return await self._get_exact_match(cache_key)
    
    async def _get_exact_match(self, cache_key: str) -> Optional[Any]:
        """Get exact match from cache levels"""
        
        # Try L1 cache first
        l1_entry = self.l1_cache.get(cache_key)
        if l1_entry:
            logger.debug(f"L1 cache hit: {cache_key}")
            return l1_entry.value
        
        # Try L2 cache
        try:
            if cache_key in self.l2_cache:
                cached_data = self.l2_cache[cache_key]
                value = self._deserialize_value(cached_data["value"])
                
                if value is not None:
                    # Promote to L1 cache
                    entry = CacheEntry(
                        key=cache_key,
                        value=value,
                        strategy=cached_data["strategy"],
                        created_at=cached_data["created_at"],
                        last_accessed=time.time(),
                        access_count=cached_data["access_count"] + 1,
                        cost_saved=cached_data["cost_saved"],
                        size_bytes=cached_data["size_bytes"]
                    )
                    
                    self.l1_cache.put(cache_key, entry)
                    logger.debug(f"L2 cache hit, promoted to L1: {cache_key}")
                    return value
        except Exception as e:
            logger.error(f"L2 cache access error: {e}")
        
        return None
    
    async def _get_semantic_match(
        self,
        service_name: str,
        operation: str,
        inputs: Dict[str, Any]
    ) -> Optional[Any]:
        """Get semantically similar match"""
        
        # Extract text for semantic comparison
        query_text = self._extract_text_for_semantic_match(inputs)
        if not query_text:
            return None
        
        # Get all cached entries for this service/operation
        cached_entries = {}
        
        # Check L1 cache
        for key, entry in self.l1_cache.items():
            if key.startswith(f"{service_name}:{operation}:"):
                cached_entries[key] = entry
        
        # Find similar entries
        similar_entries = await self.semantic_cache.find_similar_entries(query_text, cached_entries)
        
        if similar_entries:
            # Return the most similar entry
            best_key, similarity, entry = similar_entries[0]
            logger.debug(f"Semantic cache hit: {best_key} (similarity: {similarity:.3f})")
            entry.update_access()
            return entry.value
        
        return None
    
    async def _get_fuzzy_match(
        self,
        service_name: str,
        operation: str,
        inputs: Dict[str, Any]
    ) -> Optional[Any]:
        """Get fuzzy match"""
        
        # Generate base key for fuzzy matching
        base_key = f"{service_name}:{operation}"
        query_key = self._generate_cache_key(service_name, operation, inputs, CacheStrategy.EXACT_MATCH)
        
        # Get all keys that start with base key
        candidate_keys = []
        
        # From L1 cache
        for key in self.l1_cache.keys():
            if key.startswith(base_key):
                candidate_keys.append(key)
        
        # Find similar keys
        similar_keys = self.fuzzy_matcher.find_similar_keys(query_key, candidate_keys)
        
        if similar_keys:
            # Return the most similar entry
            best_key, similarity = similar_keys[0]
            entry = self.l1_cache.get(best_key)
            
            if entry:
                logger.debug(f"Fuzzy cache hit: {best_key} (similarity: {similarity:.3f})")
                return entry.value
        
        return None
    
    def _extract_text_for_semantic_match(self, inputs: Dict[str, Any]) -> str:
        """Extract text from inputs for semantic matching"""
        
        text_fields = ["prompt", "content", "text", "query", "message", "description"]
        
        text_parts = []
        
        for field in text_fields:
            if field in inputs and isinstance(inputs[field], str):
                text_parts.append(inputs[field])
        
        # Also check for nested text fields
        for key, value in inputs.items():
            if isinstance(value, str) and len(value) > 10:  # Likely to be meaningful text
                text_parts.append(value)
        
        return " ".join(text_parts) if text_parts else ""
    
    async def put(
        self,
        service_name: str,
        operation: str,
        inputs: Dict[str, Any],
        value: Any,
        strategy: CacheStrategy = CacheStrategy.EXACT_MATCH,
        ttl: Optional[float] = None,
        estimated_cost: float = 0.0
    ):
        """Put value in multi-level cache"""
        
        cache_key = self._generate_cache_key(service_name, operation, inputs, strategy)
        size_bytes = self._calculate_entry_size(value)
        
        # Create cache entry
        entry = CacheEntry(
            key=cache_key,
            value=value,
            strategy=strategy,
            created_at=time.time(),
            last_accessed=time.time(),
            access_count=0,
            cost_saved=estimated_cost,
            size_bytes=size_bytes,
            ttl=ttl,
            metadata={
                "service_name": service_name,
                "operation": operation,
                "original_text": self._extract_text_for_semantic_match(inputs)
            }
        )
        
        # Store in L1 cache
        self.l1_cache.put(cache_key, entry)
        
        # Store in L2 cache asynchronously
        asyncio.create_task(self._store_in_l2(cache_key, entry))
        
        logger.debug(f"Cached result: {cache_key} (size: {size_bytes} bytes)")
    
    async def _store_in_l2(self, cache_key: str, entry: CacheEntry):
        """Store entry in L2 cache"""
        try:
            serialized_value = self._serialize_value(entry.value)
            
            cache_data = {
                "value": serialized_value,
                "strategy": entry.strategy,
                "created_at": entry.created_at,
                "access_count": entry.access_count,
                "cost_saved": entry.cost_saved,
                "size_bytes": entry.size_bytes,
                "ttl": entry.ttl,
                "metadata": entry.metadata
            }
            
            # Set TTL if specified
            if entry.ttl:
                self.l2_cache.set(cache_key, cache_data, expire=entry.ttl)
            else:
                self.l2_cache[cache_key] = cache_data
                
        except Exception as e:
            logger.error(f"Failed to store in L2 cache: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        
        l1_stats = self.l1_cache.stats.to_dict()
        
        # L2 cache stats
        try:
            l2_volume_info = self.l2_cache.volume()
            l2_stats = {
                "size_bytes": l2_volume_info,
                "key_count": len(self.l2_cache)
            }
        except Exception:
            l2_stats = {"size_bytes": 0, "key_count": 0}
        
        # Combined stats
        total_hits = l1_stats["hits"]
        total_misses = l1_stats["misses"]
        overall_hit_rate = total_hits / (total_hits + total_misses) if (total_hits + total_misses) > 0 else 0.0
        
        return {
            "overall": {
                "hit_rate": overall_hit_rate,
                "total_cost_saved": l1_stats["total_cost_saved"]
            },
            "l1_memory": l1_stats,
            "l2_disk": l2_stats,
            "semantic_cache": {
                "embeddings_cached": len(self.semantic_cache.embeddings_cache)
            }
        }
    
    async def invalidate_pattern(self, pattern: str):
        """Invalidate cache entries matching pattern"""
        
        # Invalidate from L1
        keys_to_remove = []
        for key in self.l1_cache.keys():
            if pattern in key:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            self.l1_cache.remove(key)
        
        # Invalidate from L2
        try:
            for key in list(self.l2_cache.iterkeys()):
                if pattern in key:
                    del self.l2_cache[key]
        except Exception as e:
            logger.error(f"Failed to invalidate L2 cache pattern: {e}")
        
        logger.info(f"Invalidated {len(keys_to_remove)} cache entries matching pattern: {pattern}")
    
    async def cleanup_expired(self):
        """Clean up expired cache entries"""
        
        # Cleanup L1 cache
        expired_keys = []
        for key, entry in self.l1_cache.items():
            if entry.is_expired():
                expired_keys.append(key)
        
        for key in expired_keys:
            self.l1_cache.remove(key)
        
        logger.info(f"Cleaned up {len(expired_keys)} expired L1 cache entries")


class AICacheManager:
    """Main cache management service"""
    
    def __init__(self):
        self.cache = MultiLevelCache()
        self.hit_counts = defaultdict(int)
        self.miss_counts = defaultdict(int)
        
        # Start background cleanup task
        asyncio.create_task(self._background_maintenance())
    
    async def get_cached_result(
        self,
        service_name: str,
        operation: str,
        inputs: Dict[str, Any],
        strategy: CacheStrategy = CacheStrategy.EXACT_MATCH
    ) -> Optional[Any]:
        """Get cached result if available"""
        
        try:
            result = await self.cache.get(service_name, operation, inputs, strategy)
            
            if result is not None:
                cache_key = f"{service_name}:{operation}"
                self.hit_counts[cache_key] += 1
                logger.debug(f"Cache hit for {cache_key}")
                return result
            else:
                cache_key = f"{service_name}:{operation}"
                self.miss_counts[cache_key] += 1
                logger.debug(f"Cache miss for {cache_key}")
                return None
                
        except Exception as e:
            logger.error(f"Cache retrieval error: {e}")
            return None
    
    async def cache_result(
        self,
        service_name: str,
        operation: str,
        inputs: Dict[str, Any],
        result: Any,
        strategy: CacheStrategy = CacheStrategy.EXACT_MATCH,
        ttl: Optional[float] = None,
        estimated_cost: float = 0.0
    ):
        """Cache operation result"""
        
        try:
            await self.cache.put(
                service_name, operation, inputs, result,
                strategy, ttl, estimated_cost
            )
        except Exception as e:
            logger.error(f"Cache storage error: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        
        stats = self.cache.get_stats()
        
        # Add hit/miss counts by service
        service_stats = {}
        for key in set(list(self.hit_counts.keys()) + list(self.miss_counts.keys())):
            hits = self.hit_counts[key]
            misses = self.miss_counts[key]
            total = hits + misses
            
            service_stats[key] = {
                "hits": hits,
                "misses": misses,
                "hit_rate": hits / total if total > 0 else 0.0
            }
        
        stats["service_breakdown"] = service_stats
        
        return stats
    
    async def invalidate_cache(self, pattern: str):
        """Invalidate cache entries"""
        await self.cache.invalidate_pattern(pattern)
    
    async def _background_maintenance(self):
        """Background task for cache maintenance"""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                await self.cache.cleanup_expired()
            except Exception as e:
                logger.error(f"Cache maintenance error: {e}")


def cached(
    service_name: str,
    operation: str,
    strategy: CacheStrategy = CacheStrategy.EXACT_MATCH,
    ttl: Optional[float] = None,
    estimated_cost: float = 0.0
):
    """Decorator for caching function results"""
    
    def decorator(func):
        async def wrapper(*args, **kwargs):
            cache_manager = get_cache_manager()
            
            # Prepare inputs for caching
            inputs = {
                "args": args,
                "kwargs": kwargs
            }
            
            # Try to get cached result
            cached_result = await cache_manager.get_cached_result(
                service_name, operation, inputs, strategy
            )
            
            if cached_result is not None:
                return cached_result
            
            # Execute function
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # Cache result
            await cache_manager.cache_result(
                service_name, operation, inputs, result,
                strategy, ttl, estimated_cost
            )
            
            return result
        
        return wrapper
    return decorator


# Global cache manager instance
_cache_manager: Optional[AICacheManager] = None


def get_cache_manager() -> AICacheManager:
    """Get global cache manager instance"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = AICacheManager()
    return _cache_manager