import requests
import json
from src.procedureAgent import procedure_agent         # ✓ File: procedureAgent.py
from src.legalAdviseAgent import legal_advise_agent   # ✓ File: legalAdviseAgent.py
from src.citizen_query import query_agent              # ✓ File: citizen_query.py

# ── Config ────────────────────────────────────────────────────────────────────
import os
DATABRICKS_TOKEN = os.environ.get("DATABRICKS_TOKEN")
WORKSPACE_URL    = os.environ.get("DATABRICKS_HOST")

# ── System prompt for router ──────────────────────────────────────────────────
ROUTER_PROMPT = """You are a routing agent for an Indian legal assistance system.
You will receive a user query and decide which agents to call.

Available agents:
- "legal_advice"  : For queries where user describes a personal legal problem/situation and needs advice (what sections apply, what lawyer to approach, what documents needed)
- "procedure"     : For queries where user needs step-by-step procedural guidance (how to file, where to go, what forms, timelines, fees)
- "query"         : For general informational questions about Indian law (what does a section say, what is the punishment for X, difference between two laws)
- "fallback"      : For queries that are completely unrelated to Indian law (greetings, general knowledge, weather, jokes, etc.)

Rules:
- A query CAN map to multiple agents if it needs both advice and procedure, or both query and advice
- Only use "fallback" when the query has absolutely nothing to do with Indian law
- Return ONLY a valid JSON object, no explanation, no extra text

Response format:
{
  "agents": ["legal_advice", "procedure"],   
  "reason": "one line reason for your choice"
}

Examples:
- "My employer hasn't paid my salary for 3 months" → ["legal_advice", "procedure"]
- "What does Section 420 IPC say?" → ["query"]
- "I was arrested without warrant, what do I do and how do I file a complaint?" → ["legal_advice", "procedure"]
- "What is the difference between IPC and BNS?" → ["query"]
- "My wife is demanding dowry, I need help" → ["legal_advice", "procedure"]
- "What's the weather today?" → ["fallback"]
- "Hello, how are you?" → ["fallback"]
- "Tell me about Section 376 and also how to file a case" → ["query", "procedure"]"""

# ── Fallback responses ────────────────────────────────────────────────────────
FALLBACK_RESPONSES = {
    "greeting": "Namaste! I am your Indian Legal Assistant. I can help you with questions about Indian law, legal advice for your situation, or guide you through legal procedures. Please describe your legal query or problem.",
    "off_topic": "I'm specialized in Indian law and legal matters only. I'm unable to help with this query. Please ask me anything related to Indian laws, legal rights, legal procedures, or if you have a legal problem you need help with.",
    "default":   "I'm your Indian Legal Assistant. I can help you with:\n\n• **Legal Advice** — Understanding your legal situation, applicable sections, and what lawyer to approach\n• **Legal Procedures** — Step-by-step guidance on how to file cases, where to go, fees and timelines\n• **Law Queries** — General questions about Indian laws, sections, punishments, and legal terms\n\nPlease describe your legal query or situation."
}

# ── Step 1: Route the query ───────────────────────────────────────────────────
def route_query(user_query):
    url     = f"{WORKSPACE_URL}/serving-endpoints/databricks-meta-llama-3-3-70b-instruct/invocations"
    headers = {"Authorization": f"Bearer {DATABRICKS_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messages": [
            {"role": "system", "content": ROUTER_PROMPT},
            {"role": "user",   "content": f"Route this query: {user_query}"}
        ],
        "max_tokens": 200,
        "temperature": 0
    }
    resp = requests.post(url, headers=headers, json=payload)
    resp.raise_for_status()

    raw = resp.json()["choices"][0]["message"]["content"].strip()

    # Parse JSON safely
    try:
        decision = json.loads(raw)
    except json.JSONDecodeError:
        # Extract JSON from response if there's extra text
        start = raw.find("{")
        end   = raw.rfind("}") + 1
        decision = json.loads(raw[start:end])

    return decision

# ── Step 2: Detect fallback type for better response ─────────────────────────
def get_fallback_response(user_query):
    greetings = ["hi", "hello", "hey", "namaste", "good morning", "good evening", "how are you"]
    if any(g in user_query.lower() for g in greetings):
        return FALLBACK_RESPONSES["greeting"]
    return FALLBACK_RESPONSES["off_topic"]

# ── Step 3: Execute agents and combine results ────────────────────────────────
def execute_agents(user_query, agents_to_call):
    results = {}

    if "legal_advice" in agents_to_call:
        print("⚖️  Calling legal_advise_agent...")
        results["legal_advice"] = legal_advise_agent(user_query)

    if "procedure" in agents_to_call:
        print("📋 Calling procedure_agent...")
        results["procedure"] = procedure_agent(user_query)

    if "query" in agents_to_call:
        print("💬 Calling query_agent...")
        results["query"] = query_agent(user_query)

    return results

# ── Step 4: Format final response for UI ─────────────────────────────────────
def format_response(results, agents_called):
    if len(agents_called) == 1:
        # Single agent — return its response directly, no header needed
        return list(results.values())[0]

    # Multiple agents — add clear section headers
    sections = {
        "legal_advice": "## ⚖️ Legal Advice",
        "procedure":    "## 📋 Step-by-Step Procedure",
        "query":        "## 💬 Legal Information"
    }
    parts = []
    for agent_key in ["legal_advice", "query", "procedure"]:
        if agent_key in results:
            parts.append(f"{sections[agent_key]}\n\n{results[agent_key]}")

    return "\n\n---\n\n".join(parts)

# ── Main router ───────────────────────────────────────────────────────────────
def citizenRouter(user_query):
    print(f"\n🔀 Routing query: {user_query}\n")

    # Step 1: Get routing decision
    decision    = route_query(user_query)
    agents      = decision.get("agents", ["fallback"])
    reason      = decision.get("reason", "")

    print(f"📌 Decision: {agents} — {reason}\n")

    # Step 2: Handle fallback
    if "fallback" in agents:
        fallback_msg = get_fallback_response(user_query)
        return {
            "type":     "fallback",
            "response": fallback_msg,
            "agents":   []
        }

    # Step 3: Execute selected agents
    results = execute_agents(user_query, agents)

    # Step 4: Format and return
    final_response = format_response(results, agents)

    return {
        "type":     "answer",
        "response": final_response,
        "agents":   agents
    }
