import requests
from databricks.vector_search.client import VectorSearchClient

vsc = VectorSearchClient(disable_notice=True)

EMBEDDING_ENDPOINT = "databricks-bge-large-en"
TOP_K = 5

def embed_query(query, token, workspace_url):
    url = f"{workspace_url}/serving-endpoints/{EMBEDDING_ENDPOINT}/invocations"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, json={"input": [query]})
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]

def retrieve_from_index(query, index_name, vs_endpoint, token, workspace_url, top_k=TOP_K, columns=["id", "chunk_text"]):
    """
    Retrieve top-k chunks from a specific vector index.
    Returns list of dicts with the requested columns.
    """
    embedding = embed_query(query, token, workspace_url)
    index = vsc.get_index(endpoint_name=vs_endpoint, index_name=index_name)
    results = index.similarity_search(
        query_vector=embedding,
        columns=columns,
        num_results=top_k
    )
    data = results.get("result", {}).get("data_array", [])
    return [dict(zip(columns, row)) for row in data]

def build_context(chunks, text_key="chunk_text"):
    """
    Build a formatted context string from retrieved chunks.
    """
    if not chunks:
        return "No relevant legal information found."
    return "\n\n---\n\n".join([
        f"[Excerpt {i+1}]\n{chunk.get(text_key, '')}"
        for i, chunk in enumerate(chunks)
    ])