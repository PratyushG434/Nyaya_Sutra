import requests
import json
from src.lawyer_chat_agent import doc_chat_agent
from src.ipc_bns_agent import analyze_ipc_to_bns

import os
DATABRICKS_TOKEN = os.environ.get("DATABRICKS_TOKEN")
WORKSPACE_URL    = os.environ.get("DATABRICKS_HOST")
ROUTER_PROMPT = """You are a routing agent for a lawyer assistance system.
Decide which agent to call based on the lawyer's query and whether a file was uploaded.

Available routes:
- "ipc_conversion" : Use when the lawyer wants to CONVERT or MAP IPC sections to BNS sections.
                     The lawyer uploads a document and wants to know what IPC codes exist in it
                     and what the corresponding BNS sections are.
                     Keywords: convert, IPC to BNS, update sections, map, old to new, which BNS, 
                     remap, rewrite under BNS, modernize document

- "doc_chat"       : Use when the lawyer wants to ASK A QUESTION about an uploaded document
                     OR ask a general legal question without conversion intent.
                     Keywords: explain, what does, summarize, understand, analyze, what is,
                     what section applies, meaning of, tell me about, help me understand,
                     is this valid, review this

- "fallback"       : Use when the query is completely unrelated to law or legal documents.

Decision rules:
- File uploaded + conversion/mapping intent → "ipc_conversion"
- File uploaded + question about document   → "doc_chat" (will use the file as context)
- No file + any legal question              → "doc_chat" (will use RAG corpus)
- No file + conversion requested            → "fallback" (with upload prompt)
- Anything unrelated to law                 → "fallback"

Respond ONLY with valid JSON, no extra text:
{"route": "ipc_conversion", "reason": "one line reason"}"""

FALLBACK_RESPONSES = {
    "greeting": (
        "Namaste! I am your legal document assistant. I can help you with:\n\n"
        "• **IPC to BNS Conversion** — Upload a legal document to extract IPC sections "
        "and get detailed mapping to the new Bharatiya Nyaya Sanhita sections\n"
        "• **Document Analysis** — Ask questions about an uploaded legal document\n"
        "• **Legal Queries** — Ask general questions about Indian law\n\n"
        "Please upload a document or type your legal question."
    ),
    "off_topic": (
        "I'm specialized in Indian legal document analysis. I'm unable to help with this query. "
        "Please ask a law-related question or upload a legal document for IPC to BNS conversion."
    ),
    "no_file": (
        "It looks like you want to convert IPC sections to BNS, but no document was uploaded. "
        "Please upload the PDF legal document you want to analyze."
    )
}

def route_query(query, has_file):
    url     = f"{WORKSPACE_URL}/serving-endpoints/databricks-meta-llama-3-3-70b-instruct/invocations"
    headers = {"Authorization": f"Bearer {DATABRICKS_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messages": [
            {"role": "system", "content": ROUTER_PROMPT},
            {"role": "user",   "content": f"Query: {query}\nFile uploaded: {has_file}"}
        ],
        "max_tokens": 100,
        "temperature": 0
    }
    resp = requests.post(url, headers=headers, json=payload)
    resp.raise_for_status()

    raw = resp.json()["choices"][0]["message"]["content"].strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end   = raw.rfind("}") + 1
        return json.loads(raw[start:end])

def lawyer_router(query, file_bytes=None):
    has_file = file_bytes is not None
    query    = (query or "").strip()

    # print(f"\n🔀 Routing lawyer query (file={has_file}, query='{query}')\n")

    if has_file and not query:
        # print("📌 File uploaded with no query → auto-routing to ipc_conversion\n")
        result = analyze_ipc_to_bns(file_bytes=file_bytes)
        return {
            "type":      "ipc_conversion",
            "response":  result["response"],
            "status":    result["status"],
            "route":     "ipc_conversion",
            "used_file": True
        }

    if not has_file and not query:
        return {
            "type":     "fallback",
            "response": FALLBACK_RESPONSES["greeting"],
            "route":    "fallback"
        }

    decision = route_query(query, has_file)
    route    = decision.get("route", "fallback")
    reason   = decision.get("reason", "")
    # print(f"📌 Route: {route} — {reason}\n")

    if route == "ipc_conversion":
        if not has_file:
            return {
                "type":     "fallback",
                "response": FALLBACK_RESPONSES["no_file"],
                "route":    route
            }
        result = analyze_ipc_to_bns(file_bytes=file_bytes)
        return {
            "type":      "ipc_conversion",
            "response":  result["response"],
            "status":    result["status"],
            "route":     route,
            "used_file": True
        }

    if route == "doc_chat":
        answer = doc_chat_agent(query=query, file_bytes=file_bytes)
        return {
            "type":      "doc_chat",
            "response":  answer,
            "route":     route,
            "used_file": has_file
        }

    greetings    = ["hi", "hello", "hey", "namaste", "good morning"]
    fallback_msg = FALLBACK_RESPONSES["greeting"] if any(g in query.lower() for g in greetings) \
                   else FALLBACK_RESPONSES["off_topic"]
    return {
        "type":     "fallback",
        "response": fallback_msg,
        "route":    "fallback"
    }