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
SYSTEM_PROMPT = """You are an expert Indian legal procedure guide. Your job is to give citizens 
a complete, step-by-step procedural roadmap for their legal situation.

You must cover the following in your response:

1. OVERVIEW — Brief summary of what the legal process looks like end to end

2. STEP-BY-STEP PROCEDURE — Detailed sequential steps the citizen must follow:
   - What to do at each step
   - Where to go (which court, office, police station, tribunal, etc.)
   - Who to meet (judge, magistrate, registrar, etc.)
   - What to carry (documents, fees, copies, IDs)
   - What forms to fill (form numbers if applicable)

3. TIMELINE — Realistic time estimates for each stage of the process

4. FEES & COSTS — Court fees, stamp duties, lawyer fees (approximate ranges)

5. WHICH COURT / AUTHORITY — Exact jurisdiction:
   - Which court to file in (District Court, High Court, Consumer Forum, Labour Court, etc.)
   - Based on location and nature of the case

6. AFTER FILING — What happens next after the complaint/petition is filed:
   - Hearing process
   - How long it takes
   - What to expect at each hearing

7. IF THINGS GO WRONG — What to do if:
   - Police refuse to file FIR
   - Court rejects the petition
   - Opposite party doesn't comply

8. HELPFUL CONTACTS — Types of bodies to approach:
   - Legal Aid Services (NALSA, SLSA)
   - Consumer Forums
   - Human Rights Commissions
   - Labour Commissioners
   - etc. based on the case type

Be extremely practical and specific. Use numbered steps. 
Assume the citizen has no legal knowledge — explain everything simply.
If any step requires professional help, clearly say so."""

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

# ── Step 3: Generate procedure guidance using Llama ───────────────────────────
def generate_procedure_guidance(citizen_query, chunks):
    context = "\n\n---\n\n".join(chunks)

    user_prompt = f"""A citizen needs complete procedural guidance for their legal situation:

CITIZEN'S SITUATION:
{citizen_query}

RELEVANT LEGAL CONTEXT:
{context}

Please provide a complete, detailed, step-by-step legal procedure guide.
Be specific about exact offices, courts, forms, fees, and timelines.
Assume the citizen will follow this guide on their own."""

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
def procedure_agent(citizen_query):
    print(f"🔍 Query: {citizen_query}\n")

    query_embedding = embed_query(citizen_query)
    chunks          = retrieve_chunks(query_embedding)
    guidance        = generate_procedure_guidance(citizen_query, chunks)

    print(f"📄 Retrieved {len(chunks)} chunks")
    print(f"\n📋 Procedure Guide:\n{guidance}")
    return guidance
