import requests
import io
from PyPDF2 import PdfReader
from src.vector_search_utils import get_vector_search_client

import os
DATABRICKS_TOKEN = os.environ.get("DATABRICKS_TOKEN")
WORKSPACE_URL    = os.environ.get("DATABRICKS_HOST")

VS_ENDPOINT = "test"
INDEX_NAME  = "workspace.default.legal_corpus_delta_vs_index"
TOP_K       = 5

vsc = get_vector_search_client()

SYSTEM_PROMPT = """You are an expert legal assistant helping a lawyer understand a legal document or answer legal questions.

Answer the lawyer's question clearly and precisely. If the context is from a document they uploaded, 
refer to it directly. If it's from the legal corpus, cite the relevant sections.
Use professional legal language appropriate for a lawyer."""

# ── Extract text from uploaded PDF bytes ──────────────────────────────────────
def extract_text_from_pdf(file_bytes):
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        return " ".join([page.extract_text() or "" for page in reader.pages])
    except Exception as e:
        return f"Could not extract text: {str(e)}"

# ── Embed query ───────────────────────────────────────────────────────────────
def embed_query(query):
    url     = f"{WORKSPACE_URL}/serving-endpoints/databricks-bge-large-en/invocations"
    headers = {"Authorization": f"Bearer {DATABRICKS_TOKEN}", "Content-Type": "application/json"}
    resp    = requests.post(url, headers=headers, json={"input": [query]})
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]

# ── Retrieve from RAG corpus ──────────────────────────────────────────────────
def retrieve_chunks(query_embedding):
    index      = vsc.get_index(endpoint_name=VS_ENDPOINT, index_name=INDEX_NAME)
    results    = index.similarity_search(
        query_vector=query_embedding,
        columns=["id", "chunk_text"],
        num_results=TOP_K
    )
    data_array = results["result"]["data_array"]
    return [row[1] for row in data_array]

# ── Generate answer ───────────────────────────────────────────────────────────
def generate_answer(query, context, context_source):
    user_prompt = f"""Lawyer's question: {query}

Context (from {context_source}):
{context}

Answer the question based on the context provided."""

    url     = f"{WORKSPACE_URL}/serving-endpoints/databricks-meta-llama-3-3-70b-instruct/invocations"
    headers = {"Authorization": f"Bearer {DATABRICKS_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_prompt}
        ],
        "max_tokens": 1500,
        "temperature": 0.1
    }
    resp = requests.post(url, headers=headers, json=payload)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]

# ── Main entry point ──────────────────────────────────────────────────────────
def doc_chat_agent(query, file_bytes=None):
    """
    If file_bytes is provided → extract text from PDF and use as context.
    If not → perform RAG on legal corpus.
    """
    if file_bytes:
        # print("📄 Using uploaded document as context...")
        doc_text       = extract_text_from_pdf(file_bytes)
        # Truncate to avoid token limits — take first 6000 chars
        context        = doc_text[:6000]
        context_source = "uploaded document"
    else:
        # print("🔍 No file — retrieving from legal corpus...")
        query_embedding = embed_query(query)
        chunks          = retrieve_chunks(query_embedding)
        context         = "\n\n---\n\n".join(chunks)
        context_source  = "legal corpus"

    answer = generate_answer(query, context, context_source)
    print(f"\n💬 Answer:\n{answer}")
    return answer