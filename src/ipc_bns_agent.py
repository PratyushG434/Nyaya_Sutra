"""
IPC to BNS Legal Document Analyzer with Strict Guardrails

IPC = Indian Penal Code (India's old criminal code)
BNS = Bharatiya Nyaya Sanhita (India's new criminal code, replaced IPC in 2023)
"""

import json
import re
import io
from typing import Dict, Any, List
from PyPDF2 import PdfReader
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole
from pyspark.sql import SparkSession


def verify_legal_output(output: str, sections_info: List[Dict]) -> Dict[str, Any]:
    errors = []
    
    if "bangladesh" in output.lower():
        errors.append("CRITICAL: Output mentions 'Bangladesh' - BNS is Bharatiya Nyaya Sanhita (Indian law)")
    
    output_ipc_sections = re.findall(r'IPC Section (\d+[A-Z]?)', output)
    valid_ipc = [s["IPC_Section"] for s in sections_info]
    for section in output_ipc_sections:
        if section not in valid_ipc:
            errors.append(f"Output mentions IPC Section {section} which is not in source data")
    
    output_bns_sections = re.findall(r'BNS Section (\d+[A-Z]?(?:\(\d+\))?)', output)
    valid_bns = [s["BNS_Section"] for s in sections_info]
    for section in output_bns_sections:
        if section not in valid_bns:
            errors.append(f"Output mentions BNS Section {section} which is not in source data")
    
    for info in sections_info:
        ipc_num = info["IPC_Section"]
        bns_num = info["BNS_Section"]
        mapping_pattern = f"IPC Section {ipc_num}.*?BNS Section {bns_num}"
        if not re.search(mapping_pattern, output, re.IGNORECASE):
            errors.append(f"Missing or incorrect mapping for IPC {ipc_num} -> BNS {bns_num}")
    
    return {"valid": len(errors) == 0, "errors": errors}


def analyze_ipc_to_bns(file_bytes: bytes, spark: SparkSession = None) -> Dict[str, Any]:
    """
    Accepts raw PDF bytes (from Flask file upload) instead of a file path.
    Everything else is identical to original logic.
    """
    try:
        if spark is None:
            spark = SparkSession.builder.getOrCreate()

        w = WorkspaceClient()

        # ── Step 1: Extract text from PDF bytes ───────────────────────────────
        print("Reading PDF from bytes...")
        reader   = PdfReader(io.BytesIO(file_bytes))   # ← only change from original
        pdf_text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                pdf_text += page_text

        if not pdf_text:
            return {
                "status":   "error",
                "response": "Could not extract text from PDF. File may be empty or corrupted."
            }

        print(f"Extracted {len(pdf_text)} characters from PDF")

        # ── Step 2: Extract IPC codes using LLM ───────────────────────────────
        system_prompt = """
You are a legal document analysis system specialized in Indian Penal Code (IPC) extraction.

Task:
Extract IPC section numbers that are ACTUALLY RELEVANT to the case (charges, allegations, violations).

Rules:
- Extract sections that are:
  * Charges filed against parties
  * Allegations or complaints
  * Violations being examined
  * Legal grounds for the case
- DO NOT extract sections that are:
  * Just cited as precedents from other cases
  * Mentioned in background/context only
  * Hypothetical examples
  * In lawyer names or addresses
- Valid formats: "Section 420", "IPC 420", "420 IPC", "u/s 420", "Section 498A"
- Include subsections like "498A", "505(1)(b)"
- Remove duplicates
- Return ONLY the section numbers as strings

Output format (STRICT JSON):
{
  "ipc_codes": ["420", "302", "498A"]
}

If no relevant IPC codes found, return:
{
  "ipc_codes": []
}
"""
        print("Extracting IPC codes using LLM...")
        llm_response    = w.serving_endpoints.query(
            name="databricks-meta-llama-3-3-70b-instruct",
            messages=[
                ChatMessage(role=ChatMessageRole.SYSTEM, content=system_prompt),
                ChatMessage(role=ChatMessageRole.USER,   content=pdf_text)
            ],
            max_tokens=500
        )
        extracted_codes = json.loads(llm_response.choices[0].message.content)["ipc_codes"]
        print(f"Extracted {len(extracted_codes)} IPC codes: {extracted_codes}")

        if not extracted_codes:
            return {
                "status":   "success",
                "response": "No relevant IPC sections were identified in this legal document."
            }

        # ── Step 3: Validate against mapping table ────────────────────────────
        print("Validating codes against IPC-BNS mapping table...")
        ipc_table      = spark.table("workspace.default.ipctobns_csv_delta")
        all_valid_ipc  = [row.ipc_sections for row in ipc_table.select("ipc_sections").distinct().collect()]
        valid_codes    = [code for code in extracted_codes if code in all_valid_ipc]
        invalid_codes  = [code for code in extracted_codes if code not in all_valid_ipc]

        print(f"Valid codes: {len(valid_codes)}, Invalid codes: {len(invalid_codes)}")

        if not valid_codes:
            return {
                "status":   "success",
                "response": f"Extracted {len(extracted_codes)} IPC codes ({', '.join(extracted_codes)}), but none are in the IPC-BNS mapping table."
            }

        # ── Step 4: Fetch ground truth mappings ───────────────────────────────
        print("Fetching verified mappings from table...")
        mapping_df  = ipc_table.filter(ipc_table["ipc_sections"].isin(valid_codes))
        selected_df = mapping_df.select("ipc_sections", "bns_sections_subsections", "subject", "summary_of_comparison")
        rows        = selected_df.collect()
        sections_info = [
            {
                "IPC_Section": row["ipc_sections"],
                "BNS_Section": row["bns_sections_subsections"],
                "Subject":     row["subject"],
                "Summary":     row["summary_of_comparison"]
            }
            for row in rows
        ]

        # ── Step 5: Generate explanation ──────────────────────────────────────
        print("Generating verified legal analysis...")
        critical_definitions = """
CRITICAL DEFINITIONS (DO NOT DEVIATE):
- IPC = Indian Penal Code (India's old criminal code)
- BNS = Bharatiya Nyaya Sanhita (India's NEW criminal code that replaced IPC in 2023)
- This is INDIAN law only. Never mention Bangladesh or any other country.
- Use ONLY the exact section numbers and information provided in the data below.
- Do NOT invent, paraphrase, or add any legal interpretations not in the source data.
"""
        explanation_prompt = f"""
{critical_definitions}

Task: Write a SINGLE PARAGRAPH legal analysis of IPC to Bharatiya Nyaya Sanhita (BNS) mappings.

The document contains these IPC sections: {', '.join(valid_codes)}

For EACH section below, you MUST:
1. State: "IPC Section [exact number from data] maps to BNS Section [exact number from data]"
2. Mention the subject (use exact wording from Subject field)
3. For changes: Quote the Summary field directly, then explain practical impact
4. For no changes: State "No changes made" and briefly explain purpose
5. Connect sections with transitions ("Additionally,", "Furthermore,")

SOURCE DATA (USE EXACTLY AS PROVIDED):
{json.dumps(sections_info, indent=2)}

STRICT REQUIREMENTS:
- Write as ONE continuous paragraph
- Use EXACT section numbers from data
- Quote or closely paraphrase the Subject and Summary fields
- Do NOT invent legal details not in the data
- Use formal legal language
- Reference ONLY Indian law (Bharatiya Nyaya Sanhita)
- Start directly with the analysis
"""
        explanation_response = w.serving_endpoints.query(
            name="databricks-meta-llama-3-3-70b-instruct",
            messages=[
                ChatMessage(
                    role=ChatMessageRole.SYSTEM,
                    content="You are an Indian legal analyst. Write ONLY about Indian law. Use ONLY information from the provided data. Do not invent or paraphrase legal details. BNS = Bharatiya Nyaya Sanhita (Indian law)."
                ),
                ChatMessage(role=ChatMessageRole.USER, content=explanation_prompt)
            ],
            max_tokens=2500
        )
        detailed_explanation = explanation_response.choices[0].message.content

        # ── Step 6: Verification layer ────────────────────────────────────────
        print("Running verification checks...")
        verification = verify_legal_output(detailed_explanation, sections_info)

        if not verification["valid"]:
            print("⚠️ Verification failed:")
            for error in verification["errors"]:
                print(f"  - {error}")
            return {
                "status":   "error",
                "response": f"Verification failed. Factual errors detected: {'; '.join(verification['errors'])}"
            }

        print("✅ Verification passed")
        return {"status": "success", "response": detailed_explanation}

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return {"status": "error", "response": f"Error processing document: {str(e)}"}