from mcp.server.fastmcp import FastMCP
from typing import Literal, Annotated, Optional, List, Dict, Any, Union
from datetime import datetime, date
from dataclasses import dataclass, asdict, field
from enum import Enum
import os
import shutil

from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import VectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_chroma import Chroma
from langchain_community.vectorstores import Pinecone as LCPinecone

from mcp_arena.mcp.server import BaseMCPServer

class VectorStoreType(str, Enum):
    CHROMA = "chroma"
    PINECONE = "pinecone"
    FAISS = "faiss"

class EmbeddingType(str, Enum):
    HUGGINGFACE = "huggingface"
    OPENAI = "openai"

@dataclass
class SearchResult:
    content: str
    metadata: Dict[str, Any]
    score: float
    id: Optional[str] = None

class VectorDBMCPServer(BaseMCPServer):
    """
    MCP Server for Vector Database operations.
    Supports flexible switching between Embedding models and Vector Stores.
    """
    
    def __init__(
        self,
        store_provider: Literal["chroma", "faiss", "pinecone"] = "chroma",
        collection_name: str = "mcp_knowledge_base",
        persist_directory: str = "./vector_storage",
        embedding_provider: Literal["huggingface", "openai"] = "huggingface",
        embedding_model: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        pinecone_api_key: Optional[str] = None,
        pinecone_index_name: Optional[str] = None,
        host: str = "127.0.0.1",
        port: int = 8000,
        transport: Literal['stdio', 'sse', 'streamable-http'] = "streamable-http",
        debug: bool = False,
        auto_register_tools: bool = True,
        **base_kwargs
    ):
        """Initialize Vector DB MCP Server.
        
        Args:
            store_provider: vector database type (chroma, faiss, pinecone)
            collection_name: Name of collection/index
            persist_directory: Local path for saving data (Chroma/FAISS)
            embedding_provider: Provider for embeddings (huggingface is default)
            embedding_model: Specific model name (defaults set automatically if None)
            openai_api_key: Key if using OpenAI embeddings
            pinecone_api_key: Key if using Pinecone store
            pinecone_index_name: Index name if using Pinecone
            **base_kwargs: Base server arguments
        """
        
        self.store_provider = store_provider
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        
        # 1. Initialize Embeddings
        self.embeddings: Embeddings = self._init_embeddings(
            provider=embedding_provider,
            model=embedding_model,
            openai_key=openai_api_key
        )
        
        # 2. Initialize Vector Store
        self.vectorstore: VectorStore = self._init_vectorstore(
            provider=store_provider,
            pinecone_key=pinecone_api_key,
            pinecone_index=pinecone_index_name
        )
        
        # Initialize base class
        super().__init__(
            name=f"VectorDB Server ({store_provider}/{embedding_provider})",
            description=f"Vector operations using {store_provider} and {embedding_provider} embeddings",
            host=host,
            port=port,
            transport=transport,
            debug=debug,
            auto_register_tools=auto_register_tools,
            **base_kwargs
        )

    def _init_embeddings(self, provider: str, model: Optional[str], openai_key: Optional[str]) -> Embeddings:
        """Factory method to create the embedding model."""
        if provider == EmbeddingType.HUGGINGFACE:
            # Default to a small, fast, local model if not specified
            model_name = model or "sentence-transformers/all-MiniLM-L6-v2"
            print(f"Loading HuggingFace model locally: {model_name}...")
            return HuggingFaceEmbeddings(model_name=model_name)
            
        elif provider == EmbeddingType.OPENAI:
            api_key = openai_key or os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OpenAI API Key required for OpenAI embeddings")
            model_name = model or "text-embedding-3-small"
            return OpenAIEmbeddings(model=model_name, openai_api_key=api_key)
            
        else:
            raise ValueError(f"Unsupported embedding provider: {provider}")

    def _init_vectorstore(self, provider: str, pinecone_key: str = None, pinecone_index: str = None) -> VectorStore:
        """Factory method to create the vector store connection."""
        
        if provider == VectorStoreType.CHROMA:
            return Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embeddings,
                persist_directory=os.path.join(self.persist_directory, "chroma")
            )
            
        elif provider == VectorStoreType.FAISS:
            faiss_path = os.path.join(self.persist_directory, "faiss")
            try:
                # Try loading existing index
                return FAISS.load_local(
                    folder_path=faiss_path,
                    embeddings=self.embeddings,
                    index_name=self.collection_name,
                    allow_dangerous_deserialization=True 
                )
            except (RuntimeError, ValueError):
                # Create new empty index if not exists (Requires dummy text to init)
                print("Creating new FAISS index...")
                vs = FAISS.from_texts(["_init_marker_"], self.embeddings)
                # Remove the dummy marker immediately if possible, or handle in logic
                return vs

        elif provider == VectorStoreType.PINECONE:
            if not pinecone_key or not pinecone_index:
                raise ValueError("Pinecone credentials missing")
            return LCPinecone.from_existing_index(
                index_name=pinecone_index,
                embedding=self.embeddings
            )
            
        raise ValueError(f"Unsupported store provider: {provider}")
    
    def _register_tools(self) -> None:
        """Register all Vector DB related tools."""
        self._register_ingestion_tools()
        self._register_search_tools()
        self._register_admin_tools()

    def _register_ingestion_tools(self):
        @self.mcp_server.tool()
        def add_text_documents(
            texts: List[str], 
            metadatas: Optional[List[Dict[str, Any]]] = None
        ) -> Dict[str, Any]:
            """
            Embed and store text documents in the vector database.
            
            Args:
                texts: List of strings to store.
                metadatas: Optional list of JSON objects describing each text.
            """
            if not texts:
                return {"status": "error", "message": "No texts provided"}
            
            # Add to store
            ids = self.vectorstore.add_texts(texts=texts, metadatas=metadatas)
            
            # Handle persistence for local DBs
            self._save_local_if_needed()
                
            return {
                "status": "success", 
                "count": len(ids), 
                "ids": ids
            }

    def _register_search_tools(self):
        @self.mcp_server.tool()
        def semantic_search(
            query: str, 
            k: int = 4,
            filter_metadata: Optional[Dict[str, Any]] = None
        ) -> Dict[str, Any]:
            """
            Perform semantic similarity search on stored documents.
            
            Args:
                query: The question or concept to search for.
                k: Number of results to return (default 4).
                filter_metadata: Optional dictionary to filter results (e.g. {"category": "news"}).
            """
            # Search
            results_with_scores = self.vectorstore.similarity_search_with_score(
                query=query, 
                k=k, 
                filter=filter_metadata
            )
            
            # Format output
            formatted_results = []
            for doc, score in results_with_scores:
                # Filter out initialization markers if any
                if doc.page_content == "_init_marker_":
                    continue
                    
                formatted_results.append(asdict(
                    SearchResult(
                        content=doc.page_content,
                        metadata=doc.metadata,
                        score=float(score)
                    )
                ))
                
            return {
                "query": query,
                "total_results": len(formatted_results),
                "results": formatted_results
            }

    def _register_admin_tools(self):
        @self.mcp_server.tool()
        def reset_database() -> str:
            """
            WARNING: Deletes all data in the current collection/index.
            """
            if self.store_provider == VectorStoreType.CHROMA:
                self.vectorstore.delete_collection()
                self.vectorstore = self._init_vectorstore(self.store_provider) # Re-init
                return "Chroma collection deleted and re-initialized."
                
            elif self.store_provider == VectorStoreType.FAISS:
                # Re-create empty
                self.vectorstore = FAISS.from_texts(["_init_marker_"], self.embeddings)
                self._save_local_if_needed()
                return "FAISS index reset."
                
            return "Reset not supported via MCP for this provider (use cloud console)."

    def _save_local_if_needed(self):
        """Helper to force save for local vector stores."""
        if self.store_provider == VectorStoreType.FAISS:
            path = os.path.join(self.persist_directory, "faiss")
            self.vectorstore.save_local(path, index_name=self.collection_name)
        # Chroma saves automatically usually, but older versions might need persist calls

if __name__ == "__main__":
    # Example 1: Use HuggingFace (runs locally, free) + ChromaDB (runs locally)
    # Default transport changed to `streamable-http` to avoid reading empty STDIN
    server = VectorDBMCPServer(
        store_provider="chroma",
        embedding_provider="huggingface",
        collection_name="my_wiki_data",
        transport="streamable-http",
    )

    # Example 2: Use OpenAI + FAISS
    # server = VectorDBMCPServer(
    #     store_provider="faiss",
    #     embedding_provider="openai",
    #     openai_api_key="sk-...",
    #     transport="streamable-http",
    # )

    try:
        server.run()
    except Exception as e:
        # Provide a clearer message instead of raw JSONRPC validation spam
        import sys
        print(f"Failed to start MCP server: {e}", file=sys.stderr)
        sys.exit(1)