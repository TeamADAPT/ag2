"""
Nova Memory Manager
Handles both short-term and long-term memory management for Nova super agents.
"""

import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import logging

from ...integration.databases.db_factory import db_factory, DatabaseType
from ..model_interface import ModelInterface

logger = logging.getLogger(__name__)

class MemoryManager:
    """
    Manages Nova's memory systems including:
    - Short-term memory (Redis)
    - Long-term memory (MongoDB + Neo4j)
    - Episodic memory (PostgreSQL)
    - Semantic memory (Milvus/Chroma)
    """
    
    def __init__(self, nova_id: str):
        self.nova_id = nova_id
        self.model_interface = ModelInterface()
        self._initialize_memory_stores()
    
    async def _initialize_memory_stores(self):
        """Initialize all memory storage systems"""
        self.redis = await db_factory.get_adapter(DatabaseType.REDIS)
        self.mongo = await db_factory.get_adapter(DatabaseType.MONGODB)
        self.neo4j = await db_factory.get_adapter(DatabaseType.NEO4J)
        self.postgres = await db_factory.get_adapter(DatabaseType.POSTGRES)
        
        # Initialize vector stores
        self.milvus = await self._init_milvus()
        self.chroma = await self._init_chroma()
    
    async def store_short_term(self, data: Dict[str, Any]) -> bool:
        """
        Store data in short-term memory (Redis)
        
        Args:
            data: Data to store
            
        Returns:
            bool: Success status
        """
        try:
            # Add metadata
            data.update({
                "nova_id": self.nova_id,
                "timestamp": datetime.now().isoformat(),
                "memory_type": "short_term"
            })
            
            # Store in Redis with TTL
            key = f"stm:{self.nova_id}:{data['timestamp']}"
            await self.redis.execute(
                "SETEX",
                {
                    "key": key,
                    "seconds": 3600,  # 1 hour TTL
                    "value": json.dumps(data)
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store short-term memory: {str(e)}")
            return False
    
    async def store_long_term(self, data: Dict[str, Any]) -> bool:
        """
        Store data in long-term memory (MongoDB + Neo4j)
        
        Args:
            data: Data to store
            
        Returns:
            bool: Success status
        """
        try:
            # Add metadata
            data.update({
                "nova_id": self.nova_id,
                "timestamp": datetime.now(),
                "memory_type": "long_term"
            })
            
            # Store in MongoDB
            await self.mongo.insert("memories", data)
            
            # Create knowledge graph nodes/relationships in Neo4j
            await self._update_knowledge_graph(data)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store long-term memory: {str(e)}")
            return False
    
    async def store_episodic(self, episode: Dict[str, Any]) -> bool:
        """
        Store episodic memory (PostgreSQL)
        
        Args:
            episode: Episode data to store
            
        Returns:
            bool: Success status
        """
        try:
            # Add metadata
            episode.update({
                "nova_id": self.nova_id,
                "timestamp": datetime.now(),
                "memory_type": "episodic"
            })
            
            # Store in PostgreSQL
            await self.postgres.insert("episodes", episode)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store episodic memory: {str(e)}")
            return False
    
    async def store_semantic(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Store semantic memory (Vector stores)
        
        Args:
            text: Text to store
            metadata: Optional metadata
            
        Returns:
            bool: Success status
        """
        try:
            # Generate embeddings
            embeddings = await self.model_interface.get_embeddings(text)
            
            # Store in Milvus
            await self.milvus.insert(
                collection_name="semantic_memories",
                vectors=embeddings,
                metadata=metadata or {}
            )
            
            # Store in Chroma for redundancy
            await self.chroma.add(
                embeddings=embeddings,
                documents=[text],
                metadatas=[metadata or {}]
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store semantic memory: {str(e)}")
            return False
    
    async def retrieve_short_term(
        self,
        filter_criteria: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve short-term memories
        
        Args:
            filter_criteria: Optional filter criteria
            
        Returns:
            List[Dict[str, Any]]: Retrieved memories
        """
        try:
            # Build Redis key pattern
            pattern = f"stm:{self.nova_id}:*"
            
            # Get all matching keys
            keys = await self.redis.execute("KEYS", {"pattern": pattern})
            
            memories = []
            for key in keys:
                value = await self.redis.execute("GET", {"key": key})
                if value:
                    memory = json.loads(value)
                    if filter_criteria:
                        if all(
                            memory.get(k) == v
                            for k, v in filter_criteria.items()
                        ):
                            memories.append(memory)
                    else:
                        memories.append(memory)
            
            return memories
            
        except Exception as e:
            logger.error(f"Failed to retrieve short-term memories: {str(e)}")
            return []
    
    async def retrieve_long_term(
        self,
        filter_criteria: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve long-term memories
        
        Args:
            filter_criteria: Optional filter criteria
            
        Returns:
            List[Dict[str, Any]]: Retrieved memories
        """
        try:
            # Build base query
            query = {"nova_id": self.nova_id}
            if filter_criteria:
                query.update(filter_criteria)
            
            # Get from MongoDB
            memories = await self.mongo.find("memories", query)
            
            # Enrich with knowledge graph data
            for memory in memories:
                graph_data = await self._get_knowledge_graph_data(memory["_id"])
                memory["graph_data"] = graph_data
            
            return memories
            
        except Exception as e:
            logger.error(f"Failed to retrieve long-term memories: {str(e)}")
            return []
    
    async def retrieve_episodic(
        self,
        filter_criteria: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve episodic memories
        
        Args:
            filter_criteria: Optional filter criteria
            
        Returns:
            List[Dict[str, Any]]: Retrieved episodes
        """
        try:
            # Build base query
            query = {"nova_id": self.nova_id}
            if filter_criteria:
                query.update(filter_criteria)
            
            # Get from PostgreSQL
            episodes = await self.postgres.find("episodes", query)
            return episodes
            
        except Exception as e:
            logger.error(f"Failed to retrieve episodic memories: {str(e)}")
            return []
    
    async def retrieve_semantic(
        self,
        query_text: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieve semantic memories
        
        Args:
            query_text: Text to search for
            top_k: Number of results to return
            
        Returns:
            List[Dict[str, Any]]: Retrieved semantic memories
        """
        try:
            # Generate query embeddings
            query_embedding = await self.model_interface.get_embeddings(query_text)
            
            # Search Milvus
            milvus_results = await self.milvus.search(
                collection_name="semantic_memories",
                query_vectors=query_embedding,
                top_k=top_k
            )
            
            # Search Chroma for verification
            chroma_results = await self.chroma.query(
                query_embeddings=[query_embedding],
                n_results=top_k
            )
            
            # Combine and deduplicate results
            combined_results = []
            seen_ids = set()
            
            for result in milvus_results + chroma_results:
                if result["id"] not in seen_ids:
                    combined_results.append(result)
                    seen_ids.add(result["id"])
            
            return combined_results[:top_k]
            
        except Exception as e:
            logger.error(f"Failed to retrieve semantic memories: {str(e)}")
            return []
    
    async def _update_knowledge_graph(self, data: Dict[str, Any]):
        """Update knowledge graph with new memory data"""
        try:
            # Create memory node
            await self.neo4j.execute(
                """
                CREATE (m:Memory {
                    id: $id,
                    nova_id: $nova_id,
                    type: $type,
                    timestamp: datetime($timestamp)
                })
                """,
                {
                    "id": str(data["_id"]),
                    "nova_id": self.nova_id,
                    "type": data["memory_type"],
                    "timestamp": data["timestamp"].isoformat()
                }
            )
            
            # Extract and create entities
            entities = await self._extract_entities(data)
            for entity in entities:
                await self.neo4j.execute(
                    """
                    MERGE (e:Entity {id: $id})
                    ON CREATE SET e += $properties
                    WITH e
                    MATCH (m:Memory {id: $memory_id})
                    CREATE (m)-[:CONTAINS]->(e)
                    """,
                    {
                        "id": entity["id"],
                        "properties": entity["properties"],
                        "memory_id": str(data["_id"])
                    }
                )
            
            # Create relationships between entities
            relationships = await self._extract_relationships(entities)
            for rel in relationships:
                await self.neo4j.execute(
                    """
                    MATCH (e1:Entity {id: $from_id})
                    MATCH (e2:Entity {id: $to_id})
                    CREATE (e1)-[:RELATES {type: $type}]->(e2)
                    """,
                    {
                        "from_id": rel["from_id"],
                        "to_id": rel["to_id"],
                        "type": rel["type"]
                    }
                )
            
        except Exception as e:
            logger.error(f"Failed to update knowledge graph: {str(e)}")
            raise
    
    async def _get_knowledge_graph_data(self, memory_id: str) -> Dict[str, Any]:
        """Get knowledge graph data for a memory"""
        try:
            result = await self.neo4j.execute(
                """
                MATCH (m:Memory {id: $id})-[r:CONTAINS]->(e:Entity)
                WITH e
                MATCH (e)-[r2:RELATES]->(e2:Entity)
                RETURN e, collect(distinct {
                    relationship: type(r2),
                    entity: e2
                }) as connections
                """,
                {"id": str(memory_id)}
            )
            
            return {
                "entities": [dict(row["e"]) for row in result],
                "relationships": [
                    {
                        "from": dict(row["e"]),
                        "to": dict(conn["entity"]),
                        "type": conn["relationship"]
                    }
                    for row in result
                    for conn in row["connections"]
                ]
            }
            
        except Exception as e:
            logger.error(
                f"Failed to get knowledge graph data: {str(e)}"
            )
            return {"entities": [], "relationships": []}
    
    async def _extract_entities(
        self,
        data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Extract entities from memory data using LLM"""
        try:
            # Use LLM to extract entities
            prompt = f"""
            Extract key entities from the following data:
            {json.dumps(data)}
            
            Return a list of entities with their properties.
            """
            
            response = await self.model_interface.generate(prompt)
            return json.loads(response)
            
        except Exception as e:
            logger.error(f"Failed to extract entities: {str(e)}")
            return []
    
    async def _extract_relationships(
        self,
        entities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract relationships between entities using LLM"""
        try:
            # Use LLM to extract relationships
            prompt = f"""
            Identify relationships between these entities:
            {json.dumps(entities)}
            
            Return a list of relationships with their types.
            """
            
            response = await self.model_interface.generate(prompt)
            return json.loads(response)
            
        except Exception as e:
            logger.error(f"Failed to extract relationships: {str(e)}")
            return []
    
    async def _init_milvus(self):
        """Initialize Milvus connection"""
        try:
            from pymilvus import connections, Collection
            
            # Connect to Milvus
            connections.connect(
                alias="default",
                host=os.getenv("MILVUS_HOST", "localhost"),
                port=os.getenv("MILVUS_PORT", 19530)
            )
            
            # Get or create collection
            collection = Collection("semantic_memories")
            if not collection.is_empty:
                collection.load()
            
            return collection
            
        except Exception as e:
            logger.error(f"Failed to initialize Milvus: {str(e)}")
            return None
    
    async def _init_chroma(self):
        """Initialize Chroma connection"""
        try:
            import chromadb
            
            # Connect to Chroma
            client = chromadb.Client()
            
            # Get or create collection
            collection = client.get_or_create_collection(
                name="semantic_memories"
            )
            
            return collection
            
        except Exception as e:
            logger.error(f"Failed to initialize Chroma: {str(e)}")
            return None
