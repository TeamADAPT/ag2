"""
Nova Knowledge Manager
Manages knowledge retrieval, augmentation, and graph operations.
"""

import asyncio
from typing import Dict, List, Any, Optional, Tuple
import logging
from datetime import datetime
import json

from ...integration.databases.db_factory import db_factory, DatabaseType
from ..model_interface import ModelInterface
from .memory_manager import MemoryManager

logger = logging.getLogger(__name__)

class KnowledgeManager:
    """
    Advanced knowledge management system for Nova super agents.
    Handles:
    - RAG operations
    - GraphRAG operations
    - Knowledge graph management
    - Vector store operations
    - Knowledge synthesis
    """
    
    def __init__(self, nova_id: str):
        self.nova_id = nova_id
        self.memory_manager = MemoryManager(nova_id)
        self.model_interface = ModelInterface()
        self._initialize_knowledge_systems()
    
    async def _initialize_knowledge_systems(self):
        """Initialize knowledge management subsystems"""
        self.neo4j = await db_factory.get_adapter(DatabaseType.NEO4J)
        self.milvus = await self._init_milvus()
        self.chroma = await self._init_chroma()
    
    async def retrieve_knowledge(
        self,
        query: str,
        retrieval_type: str = "hybrid",
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Retrieve knowledge using specified approach.
        
        Args:
            query: Knowledge query
            retrieval_type: Type of retrieval (rag, graph_rag, hybrid)
            top_k: Number of results to return
            
        Returns:
            Dict[str, Any]: Retrieved knowledge
        """
        try:
            retrieval_methods = {
                "rag": self._rag_retrieval,
                "graph_rag": self._graph_rag_retrieval,
                "hybrid": self._hybrid_retrieval
            }
            
            method = retrieval_methods.get(retrieval_type)
            if not method:
                raise ValueError(f"Unknown retrieval type: {retrieval_type}")
            
            return await method(query, top_k)
            
        except Exception as e:
            logger.error(f"Knowledge retrieval failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _rag_retrieval(
        self,
        query: str,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Perform RAG-based knowledge retrieval.
        
        Args:
            query: Knowledge query
            top_k: Number of results
            
        Returns:
            Dict[str, Any]: Retrieved knowledge
        """
        try:
            # Get query embedding
            query_embedding = await self.model_interface.get_embeddings(query)
            
            # Search vector stores
            milvus_results = await self.milvus.search(
                collection_name="knowledge_base",
                query_vectors=query_embedding,
                top_k=top_k
            )
            
            chroma_results = await self.chroma.query(
                query_embeddings=[query_embedding],
                n_results=top_k
            )
            
            # Combine and rank results
            combined_results = await self._combine_vector_results(
                milvus_results,
                chroma_results
            )
            
            # Enhance with context
            enhanced_results = await self._enhance_with_context(
                query,
                combined_results
            )
            
            return {
                "success": True,
                "results": enhanced_results,
                "metadata": {
                    "query": query,
                    "timestamp": datetime.now().isoformat(),
                    "retrieval_type": "rag"
                }
            }
            
        except Exception as e:
            logger.error(f"RAG retrieval failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _graph_rag_retrieval(
        self,
        query: str,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Perform GraphRAG-based knowledge retrieval.
        
        Args:
            query: Knowledge query
            top_k: Number of results
            
        Returns:
            Dict[str, Any]: Retrieved knowledge
        """
        try:
            # Extract graph patterns
            patterns = await self._extract_graph_patterns(query)
            
            # Query knowledge graph
            graph_results = await self._query_knowledge_graph(
                patterns,
                top_k
            )
            
            # Get related vector embeddings
            vector_results = await self._get_related_vectors(
                graph_results,
                top_k
            )
            
            # Synthesize results
            synthesized = await self._synthesize_graph_and_vectors(
                graph_results,
                vector_results
            )
            
            return {
                "success": True,
                "results": synthesized,
                "metadata": {
                    "query": query,
                    "patterns": patterns,
                    "timestamp": datetime.now().isoformat(),
                    "retrieval_type": "graph_rag"
                }
            }
            
        except Exception as e:
            logger.error(f"GraphRAG retrieval failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _hybrid_retrieval(
        self,
        query: str,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Perform hybrid knowledge retrieval.
        
        Args:
            query: Knowledge query
            top_k: Number of results
            
        Returns:
            Dict[str, Any]: Retrieved knowledge
        """
        try:
            # Get results from both methods
            rag_results = await self._rag_retrieval(query, top_k)
            graph_results = await self._graph_rag_retrieval(query, top_k)
            
            # Combine results
            combined = await self._combine_retrieval_results(
                rag_results,
                graph_results
            )
            
            # Rank and deduplicate
            final_results = await self._rank_and_deduplicate(combined)
            
            return {
                "success": True,
                "results": final_results[:top_k],
                "metadata": {
                    "query": query,
                    "timestamp": datetime.now().isoformat(),
                    "retrieval_type": "hybrid"
                }
            }
            
        except Exception as e:
            logger.error(f"Hybrid retrieval failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def update_knowledge_graph(
        self,
        data: Dict[str, Any]
    ) -> bool:
        """
        Update knowledge graph with new information.
        
        Args:
            data: New knowledge to add
            
        Returns:
            bool: Success status
        """
        try:
            # Extract entities and relationships
            entities = await self._extract_entities(data)
            relationships = await self._extract_relationships(entities)
            
            # Update graph
            await self._update_graph_nodes(entities)
            await self._update_graph_relationships(relationships)
            
            # Update vector stores
            await self._update_vector_stores(data)
            
            return True
            
        except Exception as e:
            logger.error(f"Knowledge graph update failed: {str(e)}")
            return False
    
    async def _combine_vector_results(
        self,
        milvus_results: List[Dict[str, Any]],
        chroma_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Combine and rank vector store results"""
        try:
            combined = []
            seen_ids = set()
            
            # Process Milvus results
            for result in milvus_results:
                if result["id"] not in seen_ids:
                    combined.append({
                        "id": result["id"],
                        "content": result["content"],
                        "score": result["score"],
                        "source": "milvus"
                    })
                    seen_ids.add(result["id"])
            
            # Process Chroma results
            for result in chroma_results:
                if result["id"] not in seen_ids:
                    combined.append({
                        "id": result["id"],
                        "content": result["content"],
                        "score": result["score"],
                        "source": "chroma"
                    })
                    seen_ids.add(result["id"])
            
            # Sort by score
            return sorted(
                combined,
                key=lambda x: x["score"],
                reverse=True
            )
            
        except Exception as e:
            logger.error(f"Vector result combination failed: {str(e)}")
            return []
    
    async def _enhance_with_context(
        self,
        query: str,
        results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Enhance results with contextual information"""
        try:
            enhanced = []
            
            for result in results:
                # Get related context
                context = await self._get_context(result["id"])
                
                # Use LLM to enhance
                enhanced_content = await self.model_interface.generate(
                    f"""
                    Enhance the following content with context:
                    Content: {result['content']}
                    Context: {json.dumps(context)}
                    Query: {query}
                    """
                )
                
                enhanced.append({
                    **result,
                    "enhanced_content": enhanced_content,
                    "context": context
                })
            
            return enhanced
            
        except Exception as e:
            logger.error(f"Context enhancement failed: {str(e)}")
            return results
    
    async def _extract_graph_patterns(
        self,
        query: str
    ) -> List[Dict[str, Any]]:
        """Extract graph patterns from query"""
        try:
            # Use LLM to identify patterns
            patterns = await self.model_interface.generate(
                f"Extract graph patterns from: {query}"
            )
            return json.loads(patterns)
            
        except Exception as e:
            logger.error(f"Pattern extraction failed: {str(e)}")
            return []
    
    async def _query_knowledge_graph(
        self,
        patterns: List[Dict[str, Any]],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Query knowledge graph with patterns"""
        try:
            results = []
            
            for pattern in patterns:
                # Convert to Cypher
                query = self._pattern_to_cypher(pattern, limit)
                
                # Execute query
                result = await self.neo4j.execute(query)
                results.extend(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Knowledge graph query failed: {str(e)}")
            return []
    
    async def _get_related_vectors(
        self,
        graph_results: List[Dict[str, Any]],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """Get vector embeddings related to graph results"""
        try:
            vector_results = []
            
            for result in graph_results:
                # Extract text content
                text = self._extract_text_content(result)
                
                # Get embedding
                embedding = await self.model_interface.get_embeddings(text)
                
                # Search vector stores
                milvus_results = await self.milvus.search(
                    collection_name="knowledge_base",
                    query_vectors=embedding,
                    top_k=top_k
                )
                
                vector_results.extend(milvus_results)
            
            return vector_results
            
        except Exception as e:
            logger.error(f"Related vector retrieval failed: {str(e)}")
            return []
    
    async def _synthesize_graph_and_vectors(
        self,
        graph_results: List[Dict[str, Any]],
        vector_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Synthesize graph and vector results"""
        try:
            # Combine results
            combined = []
            
            for g_result in graph_results:
                # Find related vector results
                related_vectors = [
                    v for v in vector_results
                    if self._is_related(g_result, v)
                ]
                
                # Synthesize
                synthesis = await self._synthesize_entry(
                    g_result,
                    related_vectors
                )
                
                combined.append(synthesis)
            
            return combined
            
        except Exception as e:
            logger.error(f"Result synthesis failed: {str(e)}")
            return []
    
    async def _combine_retrieval_results(
        self,
        rag_results: Dict[str, Any],
        graph_results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Combine results from different retrieval methods"""
        try:
            combined = []
            seen_ids = set()
            
            # Process RAG results
            if rag_results.get("success"):
                for result in rag_results["results"]:
                    if result["id"] not in seen_ids:
                        combined.append({
                            **result,
                            "method": "rag"
                        })
                        seen_ids.add(result["id"])
            
            # Process GraphRAG results
            if graph_results.get("success"):
                for result in graph_results["results"]:
                    if result["id"] not in seen_ids:
                        combined.append({
                            **result,
                            "method": "graph_rag"
                        })
                        seen_ids.add(result["id"])
            
            return combined
            
        except Exception as e:
            logger.error(f"Result combination failed: {str(e)}")
            return []
    
    async def _rank_and_deduplicate(
        self,
        results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Rank and deduplicate results"""
        try:
            # Remove duplicates
            unique_results = []
            seen_content = set()
            
            for result in results:
                content_hash = hash(
                    json.dumps(result.get("content", ""))
                )
                
                if content_hash not in seen_content:
                    unique_results.append(result)
                    seen_content.add(content_hash)
            
            # Rank results
            ranked = sorted(
                unique_results,
                key=lambda x: x.get("score", 0),
                reverse=True
            )
            
            return ranked
            
        except Exception as e:
            logger.error(f"Ranking and deduplication failed: {str(e)}")
            return results
    
    async def _extract_entities(
        self,
        data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Extract entities from data"""
        try:
            # Use LLM to extract entities
            entities = await self.model_interface.generate(
                f"Extract entities from: {json.dumps(data)}"
            )
            return json.loads(entities)
            
        except Exception as e:
            logger.error(f"Entity extraction failed: {str(e)}")
            return []
    
    async def _extract_relationships(
        self,
        entities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract relationships between entities"""
        try:
            # Use LLM to extract relationships
            relationships = await self.model_interface.generate(
                f"Extract relationships from: {json.dumps(entities)}"
            )
            return json.loads(relationships)
            
        except Exception as e:
            logger.error(f"Relationship extraction failed: {str(e)}")
            return []
    
    async def _update_graph_nodes(
        self,
        entities: List[Dict[str, Any]]
    ) -> None:
        """Update knowledge graph nodes"""
        try:
            for entity in entities:
                await self.neo4j.execute(
                    """
                    MERGE (e:Entity {id: $id})
                    ON CREATE SET e += $properties
                    ON MATCH SET e += $properties
                    """,
                    {
                        "id": entity["id"],
                        "properties": entity["properties"]
                    }
                )
        except Exception as e:
            logger.error(f"Graph node update failed: {str(e)}")
            raise
    
    async def _update_graph_relationships(
        self,
        relationships: List[Dict[str, Any]]
    ) -> None:
        """Update knowledge graph relationships"""
        try:
            for rel in relationships:
                await self.neo4j.execute(
                    """
                    MATCH (e1:Entity {id: $from_id})
                    MATCH (e2:Entity {id: $to_id})
                    MERGE (e1)-[r:RELATES {type: $type}]->(e2)
                    ON CREATE SET r += $properties
                    ON MATCH SET r += $properties
                    """,
                    {
                        "from_id": rel["from_id"],
                        "to_id": rel["to_id"],
                        "type": rel["type"],
                        "properties": rel.get("properties", {})
                    }
                )
        except Exception as e:
            logger.error(f"Graph relationship update failed: {str(e)}")
            raise
    
    async def _update_vector_stores(
        self,
        data: Dict[str, Any]
    ) -> None:
        """Update vector stores with new data"""
        try:
            # Extract text content
            text = self._extract_text_content(data)
            
            # Generate embedding
            embedding = await self.model_interface.get_embeddings(text)
            
            # Update Milvus
            await self.milvus.insert(
                collection_name="knowledge_base",
                vectors=embedding,
                metadata=data
            )
            
            # Update Chroma
            await self.chroma.add(
                embeddings=embedding,
                documents=[text],
                metadatas=[data]
            )
            
        except Exception as e:
            logger.error(f"Vector store update failed: {str(e)}")
            raise
    
    def _pattern_to_cypher(
        self,
        pattern: Dict[str, Any],
        limit: int
    ) -> str:
        """Convert pattern to Cypher query"""
        try:
            # Extract components
            nodes = pattern.get("nodes", [])
            relationships = pattern.get("relationships", [])
            
            # Build query
            query_parts = []
            
            # Add node patterns
            for node in nodes:
                query_parts.append(
                    f"({node['label']}:{node['type']})"
                )
            
            # Add relationship patterns
            for rel in relationships:
                query_parts.append(
                    f"({rel['from']})-[:{rel['type']}]->({rel['to']})"
                )
            
            # Combine and add limit
            return f"""
            MATCH {', '.join(query_parts)}
            RETURN *
            LIMIT {limit}
            """
            
        except Exception as e:
            logger.error(f"Cypher conversion failed: {str(e)}")
            return ""
    
    def _extract_text_content(
        self,
        data: Dict[str, Any]
    ) -> str:
        """Extract text content from data"""
        try:
            # Recursively extract text
            def extract_text(obj: Any) -> str:
                if isinstance(obj, str):
                    return obj
                elif isinstance(obj, dict):
                    return " ".join(
                        extract_text(v)
                        for v in obj.values()
                    )
                elif isinstance(obj, list):
                    return " ".join(
                        extract_text(item)
                        for item in obj
                    )
                else:
                    return str(obj)
            
            return extract_text(data)
            
        except Exception as e:
            logger.error(f"Text extraction failed: {str(e)}")
            return ""
    
    def _is_related(
        self,
        graph_result: Dict[str, Any],
        vector_result: Dict[str, Any]
    ) -> bool:
        """Check if graph and vector results are related"""
        try:
            # Extract IDs
            graph_id = graph_result.get("id", "")
            vector_id = vector_result.get("id", "")
            
            # Check direct ID match
            if graph_id == vector_id:
                return True
            
            # Check content similarity
            graph_text = self._extract_text_content(graph_result)
            vector_text = self._extract_text_content(vector_result)
            
            similarity = self._calculate_similarity(
                graph_text,
                vector_text
            )
            
            return similarity > 0.7
            
        except Exception as e:
            logger.error(f"Relation check failed: {str(e)}")
            return False
    
    async def _synthesize_entry(
        self,
        graph_result: Dict[str, Any],
        vector_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Synthesize a single entry from graph and vector results"""
        try:
            # Combine content
            combined_content = {
                "graph_data": graph_result,
                "vector_data": vector_results
            }
            
            # Use LLM to synthesize
            synthesis = await self.model_interface.generate(
                f"Synthesize information: {json.dumps(combined_content)}"
            )
            
            return {
                "id": graph_result.get("id", ""),
                "content": json.loads(synthesis),
                "sources": {
                    "graph": graph_result,
                    "vectors": vector_results
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Entry synthesis failed: {str(e)}")
            return graph_result
    
    async def _get_context(
        self,
        entry_id: str
    ) -> Dict[str, Any]:
        """Get contextual information for an entry"""
        try:
            # Get graph context
            graph_context = await self.neo4j.execute(
                """
                MATCH (e:Entity {id: $id})
                OPTIONAL MATCH (e)-[r]-(related)
                RETURN e, collect({
                    relationship: type(r),
                    entity: related
                }) as connections
                """,
                {"id": entry_id}
            )
            
            # Get temporal context
            temporal_context = await self._get_temporal_context(entry_id)
            
            # Get semantic context
            semantic_context = await self._get_semantic_context(entry_id)
            
            return {
                "graph_context": graph_context,
                "temporal_context": temporal_context,
                "semantic_context": semantic_context
            }
            
        except Exception as e:
            logger.error(f"Context retrieval failed: {str(e)}")
            return {}
    
    async def _get_temporal_context(
        self,
        entry_id: str
    ) -> Dict[str, Any]:
        """Get temporal context for an entry"""
        try:
            # Query temporal information
            result = await self.neo4j.execute(
                """
                MATCH (e:Entity {id: $id})
                OPTIONAL MATCH (e)-[r:TEMPORAL_RELATION]-(t:TimePoint)
                RETURN e, collect(t) as temporal_points
                """,
                {"id": entry_id}
            )
            
            return result[0] if result else {}
            
        except Exception as e:
            logger.error(f"Temporal context retrieval failed: {str(e)}")
            return {}
    
    async def _get_semantic_context(
        self,
        entry_id: str
    ) -> Dict[str, Any]:
        """Get semantic context for an entry"""
        try:
            # Get entry content
            entry = await self.milvus.get(
                collection_name="knowledge_base",
                ids=[entry_id]
            )
            
            if not entry:
                return {}
            
            # Get embedding
            embedding = await self.model_interface.get_embeddings(
                self._extract_text_content(entry[0])
            )
            
            # Find similar entries
            similar = await self.milvus.search(
                collection_name="knowledge_base",
                query_vectors=embedding,
                top_k=5
            )
            
            return {
                "similar_entries": similar,
                "semantic_distance": self._calculate_semantic_distance(
                    embedding,
                    similar
                )
            }
            
        except Exception as e:
            logger.error(f"Semantic context retrieval failed: {str(e)}")
            return {}
    
    def _calculate_similarity(
        self,
        text1: str,
        text2: str
    ) -> float:
        """Calculate text similarity score"""
        try:
            # Simple Jaccard similarity
            set1 = set(text1.lower().split())
            set2 = set(text2.lower().split())
            
            intersection = len(set1.intersection(set2))
            union = len(set1.union(set2))
            
            return intersection / union if union > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Similarity calculation failed: {str(e)}")
            return 0.0
    
    def _calculate_semantic_distance(
        self,
        embedding: List[float],
        similar_entries: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Calculate semantic distances"""
        try:
            distances = {}
            
            for entry in similar_entries:
                distance = sum(
                    (a - b) ** 2
                    for a, b in zip(embedding, entry["embedding"])
                ) ** 0.5
                
                distances[entry["id"]] = distance
            
            return distances
            
        except Exception as e:
            logger.error(f"Distance calculation failed: {str(e)}")
            return {}
