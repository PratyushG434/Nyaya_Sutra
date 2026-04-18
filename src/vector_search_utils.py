"""
Utility for initializing Databricks Vector Search Client with proper authentication.
Works in both notebook and Databricks Apps environments.
"""
import os
from databricks.vector_search.client import VectorSearchClient

def get_vector_search_client():
    """
    Initialize and return a VectorSearchClient with proper authentication.
    
    In Databricks Apps, credentials come from environment variables.
    In notebooks, they're automatically available from the runtime context.
    """
    # Try to get credentials from environment (Databricks Apps)
    workspace_url = os.environ.get("DATABRICKS_HOST")
    token = os.environ.get("DATABRICKS_TOKEN")
    
    if workspace_url and token:
        # Databricks Apps environment - use explicit credentials
        return VectorSearchClient(
            workspace_url=workspace_url,
            personal_access_token=token,
            disable_notice=True
        )
    else:
        # Notebook environment - use default authentication
        return VectorSearchClient(disable_notice=True)
