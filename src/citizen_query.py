import requests
from databricks.vector_search.client import VectorSearchClient

# ── Config ────────────────────────────────────────────────────────────────────
VS_ENDPOINT  = "test"
INDEX_NAME   = "workspace.default.legal_corpus_delta_vs_index"
TOP_K        = 5

import os
DATABRICKS_TOKEN = os.environ.get("DATABRICKS_TOKEN")
WORKSPACE_URL    = os.environ.get("DATABRICKS_HOST")

vsc = VectorSearchClient(disable_notice=True)

# ── System prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a knowledgeable Indian law assistant. Your job is to answer 
general questions about Indian law clearly and accurately.

You may be asked things like:
- What does a particular section of IPC/BNS/any Act say?
- What is the punishment for a particular offence?
- What is the difference between two sections or laws?
- What does a legal term mean?
- Which law applies to a particular situation?
- How has a law changed (e.g. IPC to BNS)?

Guidelines:
- Answer directly and clearly
- Always mention the relevant section numbers and act names
- If a law has been replaced or amended, mention both old and new versions
- Use simple language — avoid unnecessary legal jargon
- If the answer is not in the provided context, say so honestly
- Keep answers focused and to the point"""

# ── Step 1: Embed the query ───────────────────────────────────────────────────
def embed_query(query):
    url     = f"{WORKSPACE_URL}/serving-endpoints/databricks-bge-large-en/invocations"
    headers = {"Authorization": f"Bearer {DATABRICKS_TOKEN}", "Content-Type": "application/json"}
    resp    = requests.post(url, headers=headers, json={"input": [query]})
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]

# ── Step 2: Retrieve chunks from vector index ─────────────────────────────────
def retrieve_chunks(query_embedding, top_k=TOP_K):
    index   = vsc.get_index(endpoint_name=VS_ENDPOINT, index_name=INDEX_NAME)
    results = index.similarity_search(
        query_vector=query_embedding,
        columns=["id", "chunk_text"],
        num_results=top_k
    )
    data_array = results["result"]["data_array"]
    return [row[1] for row in data_array]

# ── Step 3: Generate answer using Llama ──────────────────────────────────────
def generate_answer(user_query, chunks):
    context = "\n\n---\n\n".join(chunks)

    user_prompt = f"""Answer the following question about Indian law using the context provided.

QUESTION:
{user_query}

LEGAL CONTEXT:
{context}

Provide a clear, accurate answer. Mention specific section numbers and act names where relevant."""

    url     = f"{WORKSPACE_URL}/serving-endpoints/databricks-meta-llama-3-3-70b-instruct/invocations"
    headers = {"Authorization": f"Bearer {DATABRICKS_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_prompt}
        ],
        "max_tokens": 1024,
        "temperature": 0.1
    }
    resp = requests.post(url, headers=headers, json=payload)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]

# ── Step 4: Full pipeline ─────────────────────────────────────────────────────
def query_agent(user_query):
    print(f"🔍 Query: {user_query}\n")

    query_embedding = embed_query(user_query)
    chunks          = retrieve_chunks(query_embedding)
    answer          = generate_answer(user_query, chunks)

    print(f"📄 Retrieved {len(chunks)} chunks")
    print(f"\n💬 Answer:\n{answer}")
    return answer
