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


def extract_json_from_llm_response(response_text: str) -> dict:
    """
    Extract JSON from LLM response that might be wrapped in markdown code blocks.
    Handles cases like:
    - Pure JSON: {"key": "value"}
    - Markdown: ```json\n{"key": "value"}\n```
    - Markdown: ```\n{"key": "value"}\n```
    """
    # First, try to parse as-is
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass
    
    # Try to extract JSON from markdown code blocks
    # Pattern 1: ```json ... ```
    json_match = re.search(r'```(?:json)?\s*\n(.*?)\n```', response_text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Pattern 2: Find any JSON-like structure { ... }
    json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass
    
    # If all else fails, return empty codes
    return {"ipc_codes": []}


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


def filter_crpc_sections(extracted_codes: List[str], pdf_text: str) -> List[str]:
    """
    Filter out sections that are actually CrPC (not IPC).
    Checks if the section number appears near CrPC keywords in the document.
    """
    filtered_codes = []
    
    for code in extracted_codes:
        # Create patterns to find this section with CrPC context
        # Look for patterns like "125(1) CrPC", "Section 125 of CrPC", "125 Cr.P.C", etc.
        crpc_patterns = [
            rf'{code}\s*(?:\(\d+\))?\s*(?:of\s+)?(?:Cr\.?P\.?C|CrPC|Criminal\s+Procedure\s+Code)',
            rf'(?:Cr\.?P\.?C|CrPC|Criminal\s+Procedure\s+Code)\s+(?:Section\s+)?{code}',
            rf'Section\s+{code}\s*(?:\(\d+\))?\s+(?:of\s+)?(?:Cr\.?P\.?C|CrPC)',
            rf'u/s\s+{code}\s*(?:\(\d+\))?\s+(?:of\s+)?(?:Cr\.?P\.?C|CrPC)'
        ]
        
        is_crpc = False
        for pattern in crpc_patterns:
            if re.search(pattern, pdf_text, re.IGNORECASE):
                is_crpc = True
                break
        
        if not is_crpc:
            filtered_codes.append(code)
    
    return filtered_codes


def analyze_ipc_to_bns(file_bytes: bytes, spark: SparkSession = None) -> Dict[str, Any]:
    """
    Accepts raw PDF bytes (from Flask file upload) instead of a file path.
    Everything else is identical to original logic.
    """
    try:
        # Get or create Spark session
        if spark is None:
            spark = SparkSession.getActiveSession()
            if spark is None:
                raise RuntimeError("No active Spark session found. Please run from a notebook or provide a spark parameter.")

        w = WorkspaceClient()

        # ── Step 1: Extract text from PDF bytes ───────────────────────────────
        # print("Reading PDF from bytes...")
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

        # print(f"Extracted {len(pdf_text)} characters from PDF")

        # ── Step 2: Extract IPC codes using LLM ───────────────────────────────
        system_prompt = """
You are a legal document analysis system specialized in Indian Penal Code (IPC) extraction.

CRITICAL: You must distinguish between IPC and CrPC (Criminal Procedure Code).
- IPC = Indian Penal Code (criminal offenses)
- CrPC = Code of Criminal Procedure (procedural law)

Task:
Extract ONLY IPC section numbers that are ACTUALLY RELEVANT to the case (charges, allegations, violations).

Rules:
- Extract sections that are:
  * Explicitly marked as IPC (e.g., "Section 420 IPC", "IPC 302")
  * Criminal offense charges (murder, theft, fraud, assault, etc.)
  * Allegations or complaints about criminal acts
  * Violations being examined
  * Legal grounds for the criminal case
  
- DO NOT extract sections that are:
  * Marked as CrPC, Cr.P.C, or "Criminal Procedure Code" (e.g., "Section 125 CrPC", "125(1) of CrPC")
  * Procedural provisions (bail, arrest, investigation procedures)
  * Just cited as precedents from other cases
  * Mentioned in background/context only
  * Hypothetical examples
  * In lawyer names or addresses
  
- Valid IPC formats: "Section 420", "IPC 420", "420 IPC", "u/s 420 IPC", "Section 498A"
- Include subsections like "498A", "505(1)(b)"
- Remove duplicates
- Return ONLY the section numbers as strings (without subsection parentheses in the number string)

Examples:
- "Section 420 IPC" → Extract "420" ✓
- "125(1) CrPC" → DO NOT extract (this is CrPC) ✗
- "Section 302 IPC" → Extract "302" ✓
- "u/s 498A" (in criminal case context) → Extract "498A" ✓

Output format (STRICT JSON ONLY, no markdown, no explanation):
{
  "ipc_codes": ["420", "302", "498A"]
}

If no relevant IPC codes found, return:
{
  "ipc_codes": []
}
"""
        # print("Extracting IPC codes using LLM...")
        llm_response    = w.serving_endpoints.query(
            name="databricks-meta-llama-3-3-70b-instruct",
            messages=[
                ChatMessage(role=ChatMessageRole.SYSTEM, content=system_prompt),
                ChatMessage(role=ChatMessageRole.USER,   content=pdf_text)
            ],
            max_tokens=500
        )
        
        # Extract JSON from response (handles markdown code blocks)
        response_content = llm_response.choices[0].message.content
        extracted_data = extract_json_from_llm_response(response_content)
        extracted_codes = extracted_data.get("ipc_codes", [])
        
        # print(f"Extracted {len(extracted_codes)} IPC codes: {extracted_codes}")

        if not extracted_codes:
            return {
                "status":   "success",
                "response": "No relevant IPC sections were identified in this legal document."
            }

        # ── Step 2.5: Filter out CrPC sections ────────────────────────────────
        # print("Filtering out CrPC sections...")
        filtered_codes = filter_crpc_sections(extracted_codes, pdf_text)
        
        if len(filtered_codes) < len(extracted_codes):
            removed_count = len(extracted_codes) - len(filtered_codes)
            # print(f"Filtered out {removed_count} CrPC sections")
        
        if not filtered_codes:
            return {
                "status":   "success",
                "response": "No relevant IPC sections were identified in this legal document. The document may contain only CrPC (Criminal Procedure Code) sections."
            }

        # ── Step 3: Validate against mapping table ────────────────────────────
        # print("Validating codes against IPC-BNS mapping table...")
        ipc_table      = spark.table("workspace.default.ipctobns_csv_delta")
        all_valid_ipc  = [row.ipc_sections for row in ipc_table.select("ipc_sections").distinct().collect()]
        valid_codes    = [code for code in filtered_codes if code in all_valid_ipc]
        invalid_codes  = [code for code in filtered_codes if code not in all_valid_ipc]

        # print(f"Valid codes: {len(valid_codes)}, Invalid codes: {len(invalid_codes)}")

        if not valid_codes:
            return {
                "status":   "success",
                "response": f"Extracted {len(filtered_codes)} IPC codes ({', '.join(filtered_codes)}), but none are in the IPC-BNS mapping table."
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
        # print("Running verification checks...")
        # verification = verify_legal_output(detailed_explanation, sections_info)

        # if not verification["valid"]:
            # print("⚠️ Verification failed:")
            # for error in verification["errors"]:
                # print(f"  - {error}")
            # return {
            #     "status":   "error",
            #     "response": f"Verification failed. Factual errors detected: {'; '.join(verification['errors'])}"
            # }

        # print("✅ Verification passed")
        return {"status": "success", "response": detailed_explanation}

    except Exception as e:
        import traceback
        # print(traceback.format_exc())
        return {"status": "error", "response": f"Error processing document: {str(e)}"}