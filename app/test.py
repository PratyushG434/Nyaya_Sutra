import os
import sys
import logging
logging.getLogger("pyspark.sql.connect.logging").setLevel(logging.CRITICAL)
logging.getLogger("py4j").setLevel(logging.CRITICAL)

# ── Install dependencies ─────────────────────────────────────────────────────
import subprocess
subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "databricks-vectorsearch", "PyPDF2"])

# ── Make sure src/ is importable ─────────────────────────────────────────────
sys.path.insert(0, '/Workspace/Repos/cse240001024@iiti.ac.in/Nyaya_Sutra/app')

# ── Ensure fresh Spark session ───────────────────────────────────────────────
try:
    from pyspark.sql import SparkSession
    from databricks.sdk.runtime import spark
    # Recreate session if expired
    spark.conf.set("spark.databricks.connect.timeout", "300s")
    print("✅ Spark session refreshed")
except Exception as e:
    print(f"⚠️  Could not refresh Spark session: {e}")

# ── Set env vars if not already set (Databricks Apps sets these automatically)
if not os.environ.get("DATABRICKS_TOKEN"):
    os.environ["DATABRICKS_TOKEN"] = dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get()
if not os.environ.get("DATABRICKS_HOST"):
    os.environ["DATABRICKS_HOST"]  = dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiUrl().get()

print(f"✅ Token set: {'yes' if os.environ.get('DATABRICKS_TOKEN') else 'no'}")
print(f"✅ Host set:  {os.environ.get('DATABRICKS_HOST')}\n")

# ─────────────────────────────────────────────────────────────────────────────
# TEST 1 — Citizen chat endpoint
# ─────────────────────────────────────────────────────────────────────────────
def test_citizen_chat(query, mode="citizen"):
    print("=" * 60)
    print(f"TEST: Citizen Chat")
    # print(f"MODE: {mode}")
    print(f"QUERY: {query}")
    print("=" * 60)

    from src.citizen_router import citizenRouter

    try:
        result = citizenRouter(query)
        response = {
            "reply":  result["response"],
            "type":   result["type"],
            "agents": result["agents"]
        }
        print(f"TYPE:    {response['type']}")
        print(f"AGENTS:  {response['agents']}")
        print(f"REPLY:\n{response['reply']}")
        return response
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

# ─────────────────────────────────────────────────────────────────────────────
# TEST 2 — Lawyer chat endpoint (text query only)
# ─────────────────────────────────────────────────────────────────────────────
def test_lawyer_chat(query="", file_path=None, mode="advocate"):
    print("=" * 60)
    print(f"TEST: Lawyer Chat")
    # print(f"MODE: {mode}")
    print(f"QUERY: '{query}'")
    print(f"FILE:  {file_path if file_path else 'None'}")
    print("=" * 60)

    from src.lawyer_router import lawyer_router

    # Read file bytes if a path is given
    file_bytes = None
    if file_path:
        with open(file_path, "rb") as f:
            file_bytes = f.read()
        print(f"📄 Loaded file: {len(file_bytes)} bytes")

    if not query and file_bytes is None:
        print("❌ ERROR: Please provide a message or upload a file.")
        return {"error": "Please provide a message or upload a file."}

    try:
        result = lawyer_router(query=query, file_bytes=file_bytes)
        response = {
            "reply":     result["response"],
            # "type":      result["type"],
            # "route":     result["route"],
            # "used_file": result.get("used_file", False)
        }
        # print(f"TYPE:      {response['type']}")
        # print(f"ROUTE:     {response['route']}")
        # print(f"USED FILE: {response['used_file']}")
        # print(f"REPLY:\n{response['reply']}")
        return response
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

# ─────────────────────────────────────────────────────────────────────────────
# RUN TESTS — comment/uncomment as needed
# ─────────────────────────────────────────────────────────────────────────────

# --- Citizen tests ---
# test_citizen_chat("Hello")
test_citizen_chat("I murdered someone while defending myself , what should I do now ?")
# test_citizen_chat("My landlord locked my house illegally, what should I do?")
# test_citizen_chat("What's the weather today?")

# --- Lawyer tests (text only) ---
# test_lawyer_chat(query="What is the difference between IPC 420 and BNS equivalent?")
# test_lawyer_chat(query="Summarize the changes in theft related sections from IPC to BNS")
# test_lawyer_chat(query="Hello")

# --- Lawyer test (file only — auto IPC conversion) ---
test_lawyer_chat(file_path="/Volumes/workspace/default/hackathon_volume/State_Bank_Of_India_vs_Dr_Vijay_Mallya_on_11_July_2022.PDF")

# --- Lawyer test (file + query) ---
# test_lawyer_chat(
#     query="What IPC sections are mentioned in this document?",
#     file_path="/Volumes/workspace/default/hackathon_volume/your_document.pdf"
# )
