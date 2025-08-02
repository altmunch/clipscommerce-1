"""
Vector Database Services

Provides integration with vector databases (Pinecone, Weaviate) for
semantic search, content similarity, and brand consistency checking.
"""

import asyncio
import hashlib
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple, Union
import logging

import numpy as np
from diskcache import Cache

try:
    import pinecone
    from pinecone import Pinecone, ServerlessSpec
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False

try:
    import weaviate
    from weaviate.classes.config import Configure
    WEAVIATE_AVAILABLE = True
except ImportError:
    WEAVIATE_AVAILABLE = False

from app.core.config import settings
from app.services.ai.providers import get_embedding_service

logger = logging.getLogger(__name__)

# Setup cache for embeddings
cache = Cache("/tmp/viralos_embeddings_cache", size_limit=1000000000)  # 1GB cache


@dataclass
class VectorDocument:
    """Document for vector storage"""
    id: str
    content: str
    embedding: List[float]
    metadata: Dict[str, Any]
    namespace: str = "default"
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SearchResult:
    """Vector search result"""
    id: str
    content: str
    score: float
    metadata: Dict[str, Any]
    namespace: str = "default"


class VectorDBError(Exception):
    """Vector database operation error"""
    pass


class BaseVectorDB(ABC):
    """Abstract base class for vector databases"""
    
    def __init__(self, index_name: str):
        self.index_name = index_name
    
    @abstractmethod
    async def upsert(self, documents: List[VectorDocument]) -> bool:
        """Insert or update documents"""
        pass
    
    @abstractmethod
    async def search(
        self, 
        query_embedding: List[float], 
        namespace: str = "default",
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Search for similar vectors"""
        pass
    
    @abstractmethod
    async def delete(self, document_ids: List[str], namespace: str = "default") -> bool:
        """Delete documents by IDs"""
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        pass


class PineconeVectorDB(BaseVectorDB):
    """Pinecone vector database implementation"""
    
    def __init__(self, index_name: str = None):
        if not PINECONE_AVAILABLE:
            raise VectorDBError("Pinecone client not available. Install with: pip install pinecone-client")
        
        super().__init__(index_name or settings.PINECONE_INDEX_NAME)
        
        if not settings.PINECONE_API_KEY:
            raise VectorDBError("Pinecone API key not configured")
        
        self.client = Pinecone(api_key=settings.PINECONE_API_KEY)
        self.index = None
        self._initialize_index()
    
    def _initialize_index(self):
        """Initialize Pinecone index"""
        try:
            # Check if index exists
            existing_indexes = [idx.name for idx in self.client.list_indexes()]
            
            if self.index_name not in existing_indexes:
                logger.info(f"Creating Pinecone index: {self.index_name}")
                self.client.create_index(
                    name=self.index_name,
                    dimension=1536,  # OpenAI text-embedding-3-small dimension
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region="us-east-1"
                    )
                )
                # Wait for index to be ready
                time.sleep(10)
            
            self.index = self.client.Index(self.index_name)
            logger.info(f"Connected to Pinecone index: {self.index_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone index: {e}")
            raise VectorDBError(f"Pinecone initialization failed: {e}")
    
    async def upsert(self, documents: List[VectorDocument]) -> bool:
        """Insert or update documents in Pinecone"""
        try:
            vectors = []
            for doc in documents:
                vectors.append({
                    "id": doc.id,
                    "values": doc.embedding,
                    "metadata": {
                        **doc.metadata,
                        "content": doc.content[:1000],  # Pinecone metadata limit
                        "namespace": doc.namespace
                    }
                })
            
            # Batch upsert (Pinecone handles batching internally)
            self.index.upsert(vectors=vectors, namespace=documents[0].namespace)
            
            logger.info(f"Upserted {len(documents)} documents to Pinecone")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upsert documents to Pinecone: {e}")
            raise VectorDBError(f"Pinecone upsert failed: {e}")
    
    async def search(
        self, 
        query_embedding: List[float], 
        namespace: str = "default",
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Search for similar vectors in Pinecone"""
        try:
            response = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                namespace=namespace,
                filter=filters,
                include_metadata=True
            )
            
            results = []
            for match in response.matches:
                results.append(SearchResult(
                    id=match.id,
                    content=match.metadata.get("content", ""),
                    score=match.score,
                    metadata=match.metadata,
                    namespace=namespace
                ))
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to search Pinecone: {e}")
            raise VectorDBError(f"Pinecone search failed: {e}")
    
    async def delete(self, document_ids: List[str], namespace: str = "default") -> bool:
        """Delete documents from Pinecone"""
        try:
            self.index.delete(ids=document_ids, namespace=namespace)
            logger.info(f"Deleted {len(document_ids)} documents from Pinecone")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete documents from Pinecone: {e}")
            raise VectorDBError(f"Pinecone delete failed: {e}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get Pinecone index statistics"""
        try:
            stats = self.index.describe_index_stats()
            return {
                "total_vectors": stats.total_vector_count,
                "index_fullness": stats.index_fullness,
                "dimension": stats.dimension,
                "namespaces": dict(stats.namespaces) if stats.namespaces else {}
            }
        except Exception as e:
            logger.error(f"Failed to get Pinecone stats: {e}")
            return {}


class WeaviateVectorDB(BaseVectorDB):
    """Weaviate vector database implementation"""
    
    def __init__(self, index_name: str = "ViralOSContent"):
        if not WEAVIATE_AVAILABLE:
            raise VectorDBError("Weaviate client not available. Install with: pip install weaviate-client")
        
        super().__init__(index_name)
        
        if not settings.WEAVIATE_URL:
            raise VectorDBError("Weaviate URL not configured")
        
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Weaviate client"""
        try:
            auth_config = None
            if settings.WEAVIATE_API_KEY:
                auth_config = weaviate.auth.AuthApiKey(api_key=settings.WEAVIATE_API_KEY)
            
            self.client = weaviate.connect_to_custom(
                http_host=settings.WEAVIATE_URL.split("://")[1],
                http_secure=settings.WEAVIATE_URL.startswith("https"),
                auth_credentials=auth_config
            )
            
            # Create collection if it doesn't exist
            if not self.client.collections.exists(self.index_name):
                self.client.collections.create(
                    name=self.index_name,
                    vectorizer_config=Configure.Vectorizer.none(),  # We provide our own vectors
                    properties=[
                        weaviate.classes.config.Property(
                            name="content",
                            data_type=weaviate.classes.config.DataType.TEXT
                        ),
                        weaviate.classes.config.Property(
                            name="metadata",
                            data_type=weaviate.classes.config.DataType.OBJECT
                        ),
                        weaviate.classes.config.Property(
                            name="namespace",
                            data_type=weaviate.classes.config.DataType.TEXT
                        )
                    ]
                )
            
            logger.info(f"Connected to Weaviate collection: {self.index_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Weaviate client: {e}")
            raise VectorDBError(f"Weaviate initialization failed: {e}")
    
    async def upsert(self, documents: List[VectorDocument]) -> bool:
        """Insert or update documents in Weaviate"""
        try:
            collection = self.client.collections.get(self.index_name)
            
            with collection.batch.dynamic() as batch:
                for doc in documents:
                    batch.add_object(
                        properties={
                            "content": doc.content,
                            "metadata": doc.metadata,
                            "namespace": doc.namespace
                        },
                        uuid=doc.id,
                        vector=doc.embedding
                    )
            
            logger.info(f"Upserted {len(documents)} documents to Weaviate")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upsert documents to Weaviate: {e}")
            raise VectorDBError(f"Weaviate upsert failed: {e}")
    
    async def search(
        self, 
        query_embedding: List[float], 
        namespace: str = "default",
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Search for similar vectors in Weaviate"""
        try:
            collection = self.client.collections.get(self.index_name)
            
            where_filter = weaviate.classes.query.Filter.by_property("namespace").equal(namespace)
            if filters:
                # Add additional filters here based on your needs
                pass
            
            response = collection.query.near_vector(
                near_vector=query_embedding,
                limit=top_k,
                where=where_filter,
                return_metadata=weaviate.classes.query.MetadataQuery(distance=True)
            )
            
            results = []
            for obj in response.objects:
                results.append(SearchResult(
                    id=str(obj.uuid),
                    content=obj.properties.get("content", ""),
                    score=1 - obj.metadata.distance,  # Convert distance to similarity score
                    metadata=obj.properties.get("metadata", {}),
                    namespace=obj.properties.get("namespace", namespace)
                ))
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to search Weaviate: {e}")
            raise VectorDBError(f"Weaviate search failed: {e}")
    
    async def delete(self, document_ids: List[str], namespace: str = "default") -> bool:
        """Delete documents from Weaviate"""
        try:
            collection = self.client.collections.get(self.index_name)
            
            for doc_id in document_ids:
                collection.data.delete_by_id(doc_id)
            
            logger.info(f"Deleted {len(document_ids)} documents from Weaviate")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete documents from Weaviate: {e}")
            raise VectorDBError(f"Weaviate delete failed: {e}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get Weaviate collection statistics"""
        try:
            collection = self.client.collections.get(self.index_name)
            stats = collection.aggregate.over_all(total_count=True)
            
            return {
                "total_vectors": stats.total_count,
                "collection_name": self.index_name
            }
        except Exception as e:
            logger.error(f"Failed to get Weaviate stats: {e}")
            return {}


@dataclass
class SemanticSearchResult:
    """Enhanced search result with semantic analysis"""
    id: str
    content: str
    score: float
    metadata: Dict[str, Any]
    namespace: str
    semantic_tags: List[str] = None
    relevance_explanation: str = ""
    content_type: str = ""
    brand_alignment_score: float = 0.0


class VectorService:
    """High-level vector service with caching and optimization"""
    
    def __init__(self, provider: str = "pinecone"):
        self.provider = provider
        
        if provider == "pinecone" and PINECONE_AVAILABLE:
            self.db = PineconeVectorDB()
        elif provider == "weaviate" and WEAVIATE_AVAILABLE:
            self.db = WeaviateVectorDB()
        else:
            raise VectorDBError(f"Vector database provider '{provider}' not available")
        
        self.embedding_service = None
        self.text_service = None
    
    async def _get_embedding_service(self):
        """Get embedding service instance"""
        if self.embedding_service is None:
            self.embedding_service = await get_embedding_service()
        return self.embedding_service
    
    async def _get_text_service(self):
        """Get text service instance"""
        if self.text_service is None:
            from app.services.ai.providers import get_text_service
            self.text_service = await get_text_service()
        return self.text_service
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text"""
        return hashlib.md5(text.encode()).hexdigest()
    
    async def embed_text(self, text: str, use_cache: bool = True) -> List[float]:
        """Generate embedding for text with caching"""
        cache_key = self._get_cache_key(text)
        
        if use_cache and cache_key in cache:
            return cache[cache_key]
        
        embedding_service = await self._get_embedding_service()
        embeddings = await embedding_service.generate_embeddings([text])
        embedding = embeddings[0]
        
        if use_cache:
            cache.set(cache_key, embedding, expire=settings.CACHE_TTL_EMBEDDINGS)
        
        return embedding
    
    async def embed_texts(self, texts: List[str], use_cache: bool = True) -> List[List[float]]:
        """Generate embeddings for multiple texts with caching"""
        if not texts:
            return []
        
        embeddings = []
        uncached_texts = []
        uncached_indices = []
        
        if use_cache:
            # Check cache for each text
            for i, text in enumerate(texts):
                cache_key = self._get_cache_key(text)
                if cache_key in cache:
                    embeddings.append(cache[cache_key])
                else:
                    embeddings.append(None)
                    uncached_texts.append(text)
                    uncached_indices.append(i)
        else:
            uncached_texts = texts
            uncached_indices = list(range(len(texts)))
            embeddings = [None] * len(texts)
        
        # Generate embeddings for uncached texts
        if uncached_texts:
            embedding_service = await self._get_embedding_service()
            new_embeddings = await embedding_service.generate_embeddings(uncached_texts)
            
            # Fill in the embeddings and update cache
            for i, embedding in enumerate(new_embeddings):
                idx = uncached_indices[i]
                embeddings[idx] = embedding
                
                if use_cache:
                    cache_key = self._get_cache_key(uncached_texts[i])
                    cache.set(cache_key, embedding, expire=settings.CACHE_TTL_EMBEDDINGS)
        
        return embeddings
    
    async def add_documents(
        self, 
        contents: List[str], 
        metadatas: List[Dict[str, Any]], 
        ids: Optional[List[str]] = None,
        namespace: str = "default"
    ) -> bool:
        """Add documents to vector database"""
        if not ids:
            ids = [f"{namespace}_{i}_{int(time.time())}" for i in range(len(contents))]
        
        # Generate embeddings
        embeddings = await self.embed_texts(contents)
        
        # Create documents
        documents = []
        for i, (content, embedding, metadata) in enumerate(zip(contents, embeddings, metadatas)):
            documents.append(VectorDocument(
                id=ids[i],
                content=content,
                embedding=embedding,
                metadata=metadata,
                namespace=namespace
            ))
        
        return await self.db.upsert(documents)
    
    async def search_similar(
        self, 
        query: str, 
        namespace: str = "default",
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        similarity_threshold: float = 0.7
    ) -> List[SearchResult]:
        """Search for similar content"""
        query_embedding = await self.embed_text(query)
        results = await self.db.search(query_embedding, namespace, top_k, filters)
        
        # Filter by similarity threshold
        filtered_results = [r for r in results if r.score >= similarity_threshold]
        
        return filtered_results
    
    async def semantic_search(
        self,
        query: str,
        namespace: str = "default",
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        similarity_threshold: float = 0.7,
        include_explanations: bool = True,
        brand_guidelines: Optional[str] = None
    ) -> List[SemanticSearchResult]:
        """Advanced semantic search with AI-powered analysis"""
        
        # Get basic search results
        basic_results = await self.search_similar(
            query, namespace, top_k, filters, similarity_threshold
        )
        
        if not basic_results:
            return []
        
        # Enhance results with semantic analysis
        enhanced_results = []
        
        for result in basic_results:
            # Generate semantic tags
            semantic_tags = await self._generate_semantic_tags(result.content)
            
            # Generate relevance explanation if requested
            relevance_explanation = ""
            if include_explanations:
                relevance_explanation = await self._explain_relevance(query, result.content)
            
            # Classify content type
            content_type = await self._classify_content_type(result.content)
            
            # Calculate brand alignment if guidelines provided
            brand_alignment_score = 0.0
            if brand_guidelines:
                brand_alignment_score = await self._calculate_brand_alignment(
                    result.content, brand_guidelines
                )
            
            enhanced_results.append(SemanticSearchResult(
                id=result.id,
                content=result.content,
                score=result.score,
                metadata=result.metadata,
                namespace=result.namespace,
                semantic_tags=semantic_tags,
                relevance_explanation=relevance_explanation,
                content_type=content_type,
                brand_alignment_score=brand_alignment_score
            ))
        
        return enhanced_results
    
    async def _generate_semantic_tags(self, content: str) -> List[str]:
        """Generate semantic tags for content using AI"""
        try:
            text_service = await self._get_text_service()
            
            prompt = f"""Analyze this content and extract 5-8 semantic tags that describe its key themes, topics, and characteristics:

Content: {content[:1000]}

Return only the tags, separated by commas. Focus on:
- Main topics and themes
- Content type (educational, entertainment, promotional, etc.)
- Emotional tone
- Industry/domain
- Target audience indicators

Tags:"""
            
            response = await text_service.generate(
                prompt,
                max_tokens=100,
                temperature=0.3
            )
            
            if response.success:
                tags = [tag.strip() for tag in response.content.split(',')]
                return [tag for tag in tags if len(tag) > 2][:8]
            
        except Exception as e:
            logger.error(f"Failed to generate semantic tags: {e}")
        
        # Fallback to simple keyword extraction
        return self._extract_keywords_simple(content)
    
    def _extract_keywords_simple(self, content: str) -> List[str]:
        """Simple keyword extraction fallback"""
        import re
        from collections import Counter
        
        # Extract words, filter common stop words
        words = re.findall(r'\b\w+\b', content.lower())
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those'}
        
        filtered_words = [word for word in words if word not in stop_words and len(word) > 3]
        word_counts = Counter(filtered_words)
        
        return [word for word, count in word_counts.most_common(8)]
    
    async def _explain_relevance(self, query: str, content: str) -> str:
        """Generate explanation of why content is relevant to query"""
        try:
            text_service = await self._get_text_service()
            
            prompt = f"""Explain in 1-2 sentences why this content is relevant to the query:

Query: {query}
Content: {content[:500]}

Focus on specific connections, shared themes, or concepts that make this content relevant.

Explanation:"""
            
            response = await text_service.generate(
                prompt,
                max_tokens=100,
                temperature=0.4
            )
            
            if response.success:
                return response.content.strip()
            
        except Exception as e:
            logger.error(f"Failed to generate relevance explanation: {e}")
        
        return f"Content matches query based on semantic similarity"
    
    async def _classify_content_type(self, content: str) -> str:
        """Classify the type of content"""
        content_lower = content.lower()
        
        # Simple rule-based classification
        if any(word in content_lower for word in ['how to', 'tutorial', 'guide', 'learn', 'teach']):
            return "educational"
        elif any(word in content_lower for word in ['buy', 'purchase', 'offer', 'deal', 'discount']):
            return "promotional"
        elif any(word in content_lower for word in ['funny', 'joke', 'meme', 'lol', 'entertainment']):
            return "entertainment"
        elif any(word in content_lower for word in ['news', 'update', 'announcement', 'breaking']):
            return "news"
        elif any(word in content_lower for word in ['review', 'opinion', 'think', 'believe']):
            return "opinion"
        elif any(word in content_lower for word in ['story', 'experience', 'happened', 'journey']):
            return "narrative"
        else:
            return "general"
    
    async def _calculate_brand_alignment(self, content: str, brand_guidelines: str) -> float:
        """Calculate how well content aligns with brand guidelines"""
        try:
            # Use embeddings to calculate semantic similarity
            content_embedding = await self.embed_text(content)
            brand_embedding = await self.embed_text(brand_guidelines)
            
            # Calculate cosine similarity
            similarity = np.dot(content_embedding, brand_embedding) / (
                np.linalg.norm(content_embedding) * np.linalg.norm(brand_embedding)
            )
            
            # Convert to 0-1 score
            return max(0.0, min(1.0, (similarity + 1) / 2))
            
        except Exception as e:
            logger.error(f"Failed to calculate brand alignment: {e}")
            return 0.5  # Default neutral score
    
    async def find_brand_inconsistencies(
        self, 
        brand_guidelines: str, 
        content: str,
        namespace: str = "default",
        detailed_analysis: bool = True
    ) -> Dict[str, Any]:
        """Find brand consistency issues in content with detailed analysis"""
        
        # Calculate basic similarity
        brand_embedding = await self.embed_text(brand_guidelines)
        content_embedding = await self.embed_text(content)
        
        similarity = np.dot(brand_embedding, content_embedding) / (
            np.linalg.norm(brand_embedding) * np.linalg.norm(content_embedding)
        )
        
        # Convert to 0-1 range
        similarity_score = (similarity + 1) / 2
        is_consistent = similarity_score >= 0.7  # Adjusted threshold
        
        result = {
            "similarity_score": float(similarity_score),
            "is_consistent": is_consistent,
            "consistency_level": self._get_consistency_level(similarity_score),
            "suggestions": []
        }
        
        if detailed_analysis:
            # Get detailed brand consistency analysis
            detailed_analysis_result = await self._detailed_brand_analysis(
                brand_guidelines, content
            )
            result.update(detailed_analysis_result)
        
        # Find similar brand-compliant content for suggestions
        if not is_consistent:
            similar_content = await self.search_similar(
                content, 
                namespace=f"{namespace}_brand_examples",
                top_k=5,
                similarity_threshold=0.6
            )
            result["suggestions"] = [r.content for r in similar_content]
        
        return result
    
    def _get_consistency_level(self, score: float) -> str:
        """Convert similarity score to consistency level"""
        if score >= 0.85:
            return "excellent"
        elif score >= 0.7:
            return "good"
        elif score >= 0.5:
            return "moderate"
        elif score >= 0.3:
            return "poor"
        else:
            return "very_poor"
    
    async def _detailed_brand_analysis(
        self, 
        brand_guidelines: str, 
        content: str
    ) -> Dict[str, Any]:
        """Perform detailed brand consistency analysis using AI"""
        try:
            text_service = await self._get_text_service()
            
            prompt = f"""Analyze how well this content aligns with the brand guidelines. Provide specific feedback on consistency issues and recommendations.

Brand Guidelines:
{brand_guidelines}

Content to Analyze:
{content}

Please analyze the following aspects:
1. Tone and Voice alignment
2. Messaging consistency 
3. Value proposition alignment
4. Brand personality match
5. Target audience appropriateness

Format your response as:
TONE_ALIGNMENT: [score 1-10] - [brief explanation]
MESSAGING_CONSISTENCY: [score 1-10] - [brief explanation]  
VALUE_ALIGNMENT: [score 1-10] - [brief explanation]
PERSONALITY_MATCH: [score 1-10] - [brief explanation]
AUDIENCE_FIT: [score 1-10] - [brief explanation]
ISSUES: [list of specific issues, if any]
RECOMMENDATIONS: [list of specific recommendations]"""

            response = await text_service.generate(
                prompt,
                max_tokens=500,
                temperature=0.3
            )
            
            if response.success:
                return self._parse_brand_analysis_response(response.content)
        
        except Exception as e:
            logger.error(f"Failed to perform detailed brand analysis: {e}")
        
        return {
            "detailed_scores": {},
            "issues": [],
            "recommendations": []
        }
    
    def _parse_brand_analysis_response(self, response: str) -> Dict[str, Any]:
        """Parse AI brand analysis response"""
        result = {
            "detailed_scores": {},
            "issues": [],
            "recommendations": []
        }
        
        lines = response.strip().split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith('TONE_ALIGNMENT:'):
                score_text = line.replace('TONE_ALIGNMENT:', '').strip()
                result["detailed_scores"]["tone_alignment"] = self._extract_score_and_text(score_text)
            elif line.startswith('MESSAGING_CONSISTENCY:'):
                score_text = line.replace('MESSAGING_CONSISTENCY:', '').strip()
                result["detailed_scores"]["messaging_consistency"] = self._extract_score_and_text(score_text)
            elif line.startswith('VALUE_ALIGNMENT:'):
                score_text = line.replace('VALUE_ALIGNMENT:', '').strip()
                result["detailed_scores"]["value_alignment"] = self._extract_score_and_text(score_text)
            elif line.startswith('PERSONALITY_MATCH:'):
                score_text = line.replace('PERSONALITY_MATCH:', '').strip()
                result["detailed_scores"]["personality_match"] = self._extract_score_and_text(score_text)
            elif line.startswith('AUDIENCE_FIT:'):
                score_text = line.replace('AUDIENCE_FIT:', '').strip()
                result["detailed_scores"]["audience_fit"] = self._extract_score_and_text(score_text)
            elif line.startswith('ISSUES:'):
                current_section = "issues"
                issues_text = line.replace('ISSUES:', '').strip()
                if issues_text:
                    result["issues"].append(issues_text)
            elif line.startswith('RECOMMENDATIONS:'):
                current_section = "recommendations"
                rec_text = line.replace('RECOMMENDATIONS:', '').strip()
                if rec_text:
                    result["recommendations"].append(rec_text)
            elif current_section == "issues" and line.startswith('-'):
                result["issues"].append(line[1:].strip())
            elif current_section == "recommendations" and line.startswith('-'):
                result["recommendations"].append(line[1:].strip())
        
        return result
    
    def _extract_score_and_text(self, score_text: str) -> Dict[str, Any]:
        """Extract score and explanation from AI response"""
        import re
        
        # Try to extract score (1-10)
        score_match = re.search(r'(\d+(?:\.\d+)?)', score_text)
        score = float(score_match.group(1)) if score_match else 5.0
        
        # Extract explanation (text after score)
        explanation = re.sub(r'^\d+(?:\.\d+)?\s*-?\s*', '', score_text).strip()
        
        return {
            "score": min(10.0, max(1.0, score)),  # Clamp to 1-10 range
            "explanation": explanation
        }
    
    async def batch_brand_consistency_check(
        self,
        brand_guidelines: str,
        content_items: List[Dict[str, str]],  # [{"id": "...", "content": "..."}]
        namespace: str = "default"
    ) -> Dict[str, Dict[str, Any]]:
        """Check brand consistency for multiple content items"""
        
        results = {}
        
        # Process in batches to avoid overwhelming the AI service
        batch_size = 5
        for i in range(0, len(content_items), batch_size):
            batch = content_items[i:i + batch_size]
            
            # Process batch concurrently
            batch_tasks = []
            for item in batch:
                task = self.find_brand_inconsistencies(
                    brand_guidelines, 
                    item["content"], 
                    namespace,
                    detailed_analysis=False  # Skip detailed analysis for batch processing
                )
                batch_tasks.append((item["id"], task))
            
            # Wait for batch completion
            for item_id, task in batch_tasks:
                try:
                    result = await task
                    results[item_id] = result
                except Exception as e:
                    logger.error(f"Failed brand consistency check for {item_id}: {e}")
                    results[item_id] = {
                        "error": str(e),
                        "is_consistent": False,
                        "similarity_score": 0.0
                    }
        
        return results
    
    async def create_brand_knowledge_base(
        self,
        brand_guidelines: str,
        example_content: List[str],
        namespace: str
    ) -> bool:
        """Create a knowledge base of brand-compliant content examples"""
        
        try:
            # Add brand guidelines as a reference document
            guidelines_metadata = {
                "type": "brand_guidelines",
                "is_reference": True,
                "created_at": time.time()
            }
            
            await self.add_documents(
                contents=[brand_guidelines],
                metadatas=[guidelines_metadata],
                ids=[f"{namespace}_brand_guidelines"],
                namespace=f"{namespace}_brand_examples"
            )
            
            # Add example content
            example_metadatas = []
            example_ids = []
            
            for i, content in enumerate(example_content):
                # Check if content is brand-consistent before adding
                consistency_check = await self.find_brand_inconsistencies(
                    brand_guidelines, content, namespace, detailed_analysis=False
                )
                
                if consistency_check["is_consistent"]:
                    example_metadatas.append({
                        "type": "brand_example",
                        "consistency_score": consistency_check["similarity_score"],
                        "created_at": time.time()
                    })
                    example_ids.append(f"{namespace}_example_{i}")
            
            if example_metadatas:
                # Only add content that passed brand consistency check
                consistent_content = [
                    content for i, content in enumerate(example_content)
                    if i < len(example_ids)  # Only content that passed the check
                ]
                
                await self.add_documents(
                    contents=consistent_content,
                    metadatas=example_metadatas,
                    ids=example_ids,
                    namespace=f"{namespace}_brand_examples"
                )
            
            logger.info(f"Created brand knowledge base with {len(example_metadatas)} examples")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create brand knowledge base: {e}")
            return False
    
    async def get_content_clusters(
        self, 
        namespace: str = "default",
        min_cluster_size: int = 3
    ) -> List[Dict[str, Any]]:
        """Get content clusters for trend analysis"""
        # This is a simplified clustering approach
        # In production, you might want to use more sophisticated clustering algorithms
        
        # Search for all content in namespace (this is not efficient for large datasets)
        # You would implement pagination and proper clustering algorithms
        dummy_query = "general content"  # This is not ideal - better to retrieve all vectors
        all_results = await self.search_similar(dummy_query, namespace, top_k=1000)
        
        # Simple clustering based on similarity scores
        clusters = []
        processed_ids = set()
        
        for result in all_results:
            if result.id in processed_ids:
                continue
            
            cluster = [result]
            processed_ids.add(result.id)
            
            # Find similar content to form a cluster
            similar = await self.search_similar(
                result.content, 
                namespace, 
                top_k=20,
                similarity_threshold=0.85
            )
            
            for sim_result in similar:
                if sim_result.id not in processed_ids and len(cluster) < 10:
                    cluster.append(sim_result)
                    processed_ids.add(sim_result.id)
            
            if len(cluster) >= min_cluster_size:
                clusters.append({
                    "representative_content": result.content,
                    "cluster_size": len(cluster),
                    "average_score": sum(r.score for r in cluster) / len(cluster),
                    "items": [{"id": r.id, "content": r.content[:200]} for r in cluster]
                })
        
        return sorted(clusters, key=lambda x: x["cluster_size"], reverse=True)
    
    async def cleanup_old_embeddings(self, namespace: str, days_old: int = 30) -> int:
        """Clean up old embeddings to save storage costs"""
        # This would need to be implemented based on your metadata structure
        # For now, it's a placeholder
        logger.info(f"Cleanup requested for {namespace} older than {days_old} days")
        return 0


# Global service instance
_vector_service: Optional[VectorService] = None


async def get_vector_service(provider: str = None) -> VectorService:
    """Get global vector service instance"""
    global _vector_service
    
    if _vector_service is None:
        provider = provider or ("pinecone" if PINECONE_AVAILABLE else "weaviate")
        _vector_service = VectorService(provider)
    
    return _vector_service