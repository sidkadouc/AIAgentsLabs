# components/plugins/vector_search_plugin.py
import logging
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from azure.search.documents.models import VectorFilterMode
from azure.search.documents import SearchClient
# Updated import path for semantic-kernel
from semantic_kernel.functions import kernel_function

logger = logging.getLogger(__name__)

class VectorSearchResult(BaseModel):
    content: str
    score: Optional[float] = None

class VectorSearchPlugin:
    """Plugin for vector-based search using Azure Cognitive Search for support FAQ information."""
    
    def __init__(self, search_client: SearchClient = None, vector_field: str = "text_vector"):
        """
        Initialize the vector search plugin.
        
        Args:
            search_client: Azure Cognitive Search client (optional)
            vector_field: Name of the vector field in your index
        """
        self.search_client = search_client
        self.vector_field = vector_field
        logger.info(f"VectorSearchPlugin initialized with vector field '{vector_field}'")
    
    @kernel_function(
        description="Search for FAQ information related to user questions",
        name="search_vector_store"
    )
    def search_vector_store(
        self, 
        query: str,
        top: int = 5
    ) -> str:
        """
        Search for support FAQ information using semantic vector search.
        
        Args:
            query: The user question to search for
            top: Number of results to return
            
        Returns:
            List of search results with content only
        """
        try:
            logger.info(f"VECTOR_SEARCH_CALLED - Query: '{query}', Top: {top}")
            
            if not self.search_client:
                logger.warning("Azure Search not configured, returning empty results")
                return "No search results available - Azure Search not configured."
            
            # Create vectorizable text query
            from azure.search.documents.models import VectorizableTextQuery
            vector_query = VectorizableTextQuery(
                text=query,
                k_nearest_neighbors=20,  # Get more results for post-filtering
                fields=self.vector_field
            )

            logger.debug(f"Executing vector query with k_nearest_neighbors=20, fields={self.vector_field}")

            # Execute search without filter expression
            search_results = self.search_client.search(
                search_text=None,
                vector_queries=[vector_query],
                select=["chunk", "title", "entity", "language"],
                top=20  # Get more results for post-filtering
            )
            
            # Format the results
            sources_formatted = ""
            if search_results:
                sources_formatted = "=================\n".join([
                    f'TITLE: {document.get("title", "")}, '
                    f'CONTENT: {document.get("chunk", "")}, '
                    f'entity: {document.get("entity", "")}'
                    for document in search_results
                ])
            
            # Log the top result if any
            if search_results:
                logger.info(f"search result: {sources_formatted}")
            else:
                logger.warning(f"No matching results found for query '{query}'")
                
            return sources_formatted
            
        except Exception as e:
            logger.error(f"VECTOR_SEARCH_ERROR - Error executing FAQ search: {e}")
            return f"Search error: {str(e)}"
