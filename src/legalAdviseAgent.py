import requests
from databricks.vector_search.client import VectorSearchClient

# ── Config ────────────────────────────────────────────────────────────────────
VS_ENDPOINT  = "test"
INDEX_NAME   = "workspace.default.legal_corpus_delta_vs_index"
TOP_K        = 6

import os
DATABRICKS_TOKEN = os.environ.get("DATABRICKS_TOKEN")
WORKSPACE_URL    = os.environ.get("DATABRICKS_HOST")
vsc = VectorSearchClient(disable_notice=True)

# ── System prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are an expert Indian legal advisor helping citizens understand their legal situation.

Given a citizen's problem and relevant legal context, provide a structured response covering:

1. CASE TYPE — What kind of legal case this is (civil, criminal, consumer, family, etc.)
2. APPLICABLE SECTIONS — Specific IPC/BNS/Act sections relevant to the situation
3. DOCUMENTS REQUIRED — List of documents the citizen should gather immediately
4. TYPE OF LAWYER — What kind of lawyer to approach
5. IMMEDIATE ACTIONS — Concrete steps the citizen can take right now
6. IMPORTANT WARNINGS — Any deadlines, statute of limitations, or critical cautions

Be clear, practical, and empathetic. If urgency is involved (domestic violence, illegal detention), highlight it at the top.
Base your advice strictly on the provided legal context. If something is not covered, say so honestly."""

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

# ── Step 3: Generate legal advice using Llama ─────────────────────────────────
def generate_legal_advice(citizen_query, chunks):
    context = "\n\n---\n\n".join(chunks)
    
    user_prompt = f"""A citizen has come to you with the following problem:

CITIZEN'S PROBLEM:
{citizen_query}

RELEVANT LEGAL CONTEXT:
{context}

Please provide structured legal advice covering all the points in your instructions.
Be specific about section numbers, document names, and actionable steps."""

    url     = f"{WORKSPACE_URL}/serving-endpoints/databricks-meta-llama-3-3-70b-instruct/invocations"
    headers = {"Authorization": f"Bearer {DATABRICKS_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_prompt}
        ],
        "max_tokens": 2048,
        "temperature": 0.1
    }
    resp = requests.post(url, headers=headers, json=payload)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]

# ── Step 4: Full pipeline ─────────────────────────────────────────────────────
def legal_advise_agent(citizen_query):
    print(f"🔍 Query: {citizen_query}\n")

    query_embedding = embed_query(citizen_query)
    chunks          = retrieve_chunks(query_embedding)
    advice          = generate_legal_advice(citizen_query, chunks)

    print(f"📄 Retrieved {len(chunks)} chunks")
    print(f"\n⚖️ Legal Advice:\n{advice}")
    return advice
