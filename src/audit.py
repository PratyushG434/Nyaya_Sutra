"""Document Audit — Advanced legal document analyzer for advocates.

Scans legal documents to:
- Extract all legal citations (statutes, case law)
- Map outdated IPC references to modern BNS equivalents
- Flag repealed/outdated provisions
- Generate detailed severity reports
- Provide replacement suggestions
"""

from __future__ import annotations
import re
import logging
from typing import Optional, Literal
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

log = logging.getLogger(__name__)


# ==================== IPC to BNS Mapping ====================

class CitationStatus(Enum):
    """Status of a legal citation."""
    VALID = "valid"
    OUTDATED = "outdated"
    REPEALED = "repealed"
    AMENDED = "amended"
    UNKNOWN = "unknown"


class SeverityLevel(Enum):
    """Severity level for legal issues."""
    CRITICAL = "critical"  # Repealed provisions, serious errors
    HIGH = "high"  # Outdated provisions needing immediate update
    MEDIUM = "medium"  # Minor issues, style problems
    LOW = "low"  # Suggestions, best practices
    INFO = "info"  # Informational notes


# IPC to BNS mapping database (sample - expand as needed)
IPC_TO_BNS_MAPPING = json


# Citation pattern regex
CITATION_PATTERNS = {
    "ipc": re.compile(r'\b(?:IPC|Indian Penal Code)\s*(?:Section|Sec\.?|§)?\s*(\d+[A-Z]?)\b', re.IGNORECASE),
    "bns": re.compile(r'\b(?:BNS|Bharatiya Nyaya Sanhita)\s*(?:Section|Sec\.?|§)?\s*(\d+[A-Z]?)\b', re.IGNORECASE),
    "crpc": re.compile(r'\b(?:CrPC|Cr\.?P\.?C\.?|Code of Criminal Procedure)\s*(?:Section|Sec\.?|§)?\s*(\d+[A-Z]?)\b', re.IGNORECASE),
    "cpc": re.compile(r'\b(?:CPC|C\.?P\.?C\.?|Civil Procedure Code)\s*(?:Section|Sec\.?|§)?\s*(\d+[A-Z]?)\b', re.IGNORECASE),
    "case": re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+v\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*(?:\((\d{4})\))?\s*(?:(\d+)\s+(?:SCC|SCR|AIR))?\b'),
}


# ==================== Data Models ====================

@dataclass
class Citation:
    """Represents a legal citation found in document."""
    citation_type: str  # "ipc", "bns", "crpc", "cpc", "case"
    citation_text: str  # Original text as found
    section_number: str  # Normalized section number
    line_number: int
    position: tuple[int, int]  # Start, end position in text
    status: CitationStatus = CitationStatus.UNKNOWN
    replacement: Optional[str] = None
    title: str = ""
    notes: str = ""
    severity: SeverityLevel = SeverityLevel.INFO


@dataclass
class AuditIssue:
    """Represents an issue found during audit."""
    severity: SeverityLevel
    category: str  # "outdated_provision", "repealed_statute", "style_issue", etc.
    message: str
    citation: Optional[Citation] = None
    suggestion: str = ""
    line_number: Optional[int] = None
    auto_fixable: bool = False


@dataclass
class AuditReport:
    """Complete document audit report."""
    document_name: str
    audit_date: datetime
    total_citations: int
    citations: list[Citation]
    issues: list[AuditIssue]
    severity_counts: dict[str, int]
    ipc_to_bns_mappings: list[dict]
    summary: str
    
    def get_critical_issues(self) -> list[AuditIssue]:
        """Get all critical severity issues."""
        return [i for i in self.issues if i.severity == SeverityLevel.CRITICAL]
    
    def get_auto_fixable_issues(self) -> list[AuditIssue]:
        """Get issues that can be automatically fixed."""
        return [i for i in self.issues if i.auto_fixable]
    
    def get_issues_by_severity(self, severity: SeverityLevel) -> list[AuditIssue]:
        """Get issues of specific severity."""
        return [i for i in self.issues if i.severity == severity]


# ==================== Document Audit Agent ====================

class DocumentAuditAgent:
    """Advanced legal document auditor."""
    
    def __init__(
        self,
        strict_mode: bool = True,
        check_ipc_bns: bool = True,
        check_case_citations: bool = True,
        custom_mappings: Optional[dict] = None
    ):
        """
        Initialize document audit agent.
        
        Args:
            strict_mode: Flag all outdated provisions as CRITICAL
            check_ipc_bns: Check for IPC to BNS mapping issues
            check_case_citations: Validate case citations
            custom_mappings: Additional IPC to BNS mappings
        """
        self.strict_mode = strict_mode
        self.check_ipc_bns = check_ipc_bns
        self.check_case_citations = check_case_citations
        
        # Merge custom mappings
        self.ipc_bns_map = IPC_TO_BNS_MAPPING.copy()
        if custom_mappings:
            self.ipc_bns_map.update(custom_mappings)
    
    def audit_document(
        self,
        document_text: str,
        document_name: str = "Untitled Document"
    ) -> AuditReport:
        """
        Perform comprehensive audit of legal document.
        
        Args:
            document_text: Text content of the document
            document_name: Name/identifier for the document
        
        Returns:
            Complete audit report
        """
        log.info(f"Starting audit of document: {document_name}")
        
        # Extract all citations
        citations = self._extract_citations(document_text)
        
        # Identify issues
        issues = []
        ipc_mappings = []
        
        for citation in citations:
            # Check IPC citations
            if citation.citation_type == "ipc" and self.check_ipc_bns:
                issue, mapping = self._check_ipc_citation(citation)
                if issue:
                    issues.append(issue)
                if mapping:
                    ipc_mappings.append(mapping)
            
            # Check BNS citations
            elif citation.citation_type == "bns":
                citation.status = CitationStatus.VALID
                citation.severity = SeverityLevel.INFO
            
            # Check case citations
            elif citation.citation_type == "case" and self.check_case_citations:
                issue = self._check_case_citation(citation)
                if issue:
                    issues.append(issue)
        
        # Count severity levels
        severity_counts = {
            "critical": sum(1 for i in issues if i.severity == SeverityLevel.CRITICAL),
            "high": sum(1 for i in issues if i.severity == SeverityLevel.HIGH),
            "medium": sum(1 for i in issues if i.severity == SeverityLevel.MEDIUM),
            "low": sum(1 for i in issues if i.severity == SeverityLevel.LOW),
            "info": sum(1 for i in issues if i.severity == SeverityLevel.INFO),
        }
        
        # Generate summary
        summary = self._generate_summary(len(citations), issues, ipc_mappings)
        
        report = AuditReport(
            document_name=document_name,
            audit_date=datetime.now(),
            total_citations=len(citations),
            citations=citations,
            issues=issues,
            severity_counts=severity_counts,
            ipc_to_bns_mappings=ipc_mappings,
            summary=summary
        )
        
        log.info(f"Audit complete. Found {len(citations)} citations, {len(issues)} issues")
        return report
    
    def _extract_citations(self, text: str) -> list[Citation]:
        """Extract all legal citations from text."""
        citations = []
        lines = text.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            # Check each citation type
            for cit_type, pattern in CITATION_PATTERNS.items():
                for match in pattern.finditer(line):
                    if cit_type in ["ipc", "bns", "crpc", "cpc"]:
                        section = match.group(1)
                        citation = Citation(
                            citation_type=cit_type,
                            citation_text=match.group(0),
                            section_number=section,
                            line_number=line_num,
                            position=(match.start(), match.end())
                        )
                    else:  # case citation
                        citation = Citation(
                            citation_type="case",
                            citation_text=match.group(0),
                            section_number="",
                            line_number=line_num,
                            position=(match.start(), match.end())
                        )
                    
                    citations.append(citation)
        
        return citations
    
    def _check_ipc_citation(self, citation: Citation) -> tuple[Optional[AuditIssue], Optional[dict]]:
        """Check IPC citation and suggest BNS replacement."""
        section_key = f"IPC {citation.section_number}"
        
        if section_key in self.ipc_bns_map:
            mapping_info = self.ipc_bns_map[section_key]
            
            # Update citation
            citation.status = mapping_info["status"]
            citation.replacement = mapping_info["bns"]
            citation.title = mapping_info["title"]
            citation.notes = mapping_info["notes"]
            citation.severity = SeverityLevel.CRITICAL if self.strict_mode else SeverityLevel.HIGH
            
            # Create issue
            issue = AuditIssue(
                severity=citation.severity,
                category="outdated_provision",
                message=f"IPC Section {citation.section_number} has been repealed",
                citation=citation,
                suggestion=f"Replace with {mapping_info['bns']}: {mapping_info['title']}",
                line_number=citation.line_number,
                auto_fixable=True
            )
            
            # Create mapping record
            mapping = {
                "ipc_section": section_key,
                "bns_section": mapping_info["bns"],
                "title": mapping_info["title"],
                "line_number": citation.line_number,
                "original_text": citation.citation_text
            }
            
            return issue, mapping
        
        else:
            # IPC citation but no mapping found
            citation.status = CitationStatus.UNKNOWN
            citation.severity = SeverityLevel.MEDIUM
            
            issue = AuditIssue(
                severity=SeverityLevel.MEDIUM,
                category="unmapped_ipc",
                message=f"IPC Section {citation.section_number} found but BNS mapping unknown",
                citation=citation,
                suggestion="Verify if this provision has been repealed and find BNS equivalent",
                line_number=citation.line_number,
                auto_fixable=False
            )
            
            return issue, None
    
    def _check_case_citation(self, citation: Citation) -> Optional[AuditIssue]:
        """Check case citation format and validity."""
        # Basic format validation
        if not re.search(r'\d{4}', citation.citation_text):  # No year
            return AuditIssue(
                severity=SeverityLevel.LOW,
                category="citation_format",
                message="Case citation missing year",
                citation=citation,
                suggestion="Add year for complete citation",
                line_number=citation.line_number,
                auto_fixable=False
            )
        
        return None
    
    def _generate_summary(
        self,
        total_citations: int,
        issues: list[AuditIssue],
        ipc_mappings: list[dict]
    ) -> str:
        """Generate human-readable audit summary."""
        lines = []
        
        if total_citations == 0:
            return "No legal citations found in document."
        
        lines.append(f"Found {total_citations} legal citations.")
        
        if not issues:
            lines.append("✅ No issues detected. All citations appear valid.")
        else:
            critical = sum(1 for i in issues if i.severity == SeverityLevel.CRITICAL)
            high = sum(1 for i in issues if i.severity == SeverityLevel.HIGH)
            
            if critical > 0:
                lines.append(f"⚠️ CRITICAL: {critical} repealed provisions must be updated immediately.")
            if high > 0:
                lines.append(f"⚠️ HIGH: {high} outdated provisions need attention.")
            
            if ipc_mappings:
                lines.append(f"📋 Found {len(ipc_mappings)} IPC provisions with BNS replacements.")
        
        return " ".join(lines)
    
    def export_markdown_report(self, report: AuditReport) -> str:
        """Export audit report as formatted markdown."""
        lines = [
            f"# Legal Document Audit Report",
            f"**Document**: {report.document_name}",
            f"**Audit Date**: {report.audit_date.strftime('%Y-%m-%d %H:%M')}",
            "",
            "---",
            "",
            "## Summary",
            report.summary,
            "",
            f"**Total Citations**: {report.total_citations}",
            f"**Total Issues**: {len(report.issues)}",
            "",
            "### Issue Breakdown",
            f"* 🔴 Critical: {report.severity_counts['critical']}",
            f"* 🟠 High: {report.severity_counts['high']}",
            f"* 🟡 Medium: {report.severity_counts['medium']}",
            f"* 🟢 Low: {report.severity_counts['low']}",
            "",
            "---",
            "",
        ]
        
        # IPC to BNS mappings
        if report.ipc_to_bns_mappings:
            lines.append("## IPC to BNS Mappings Required")
            lines.append("")
            for mapping in report.ipc_to_bns_mappings:
                lines.append(f"### Line {mapping['line_number']}: {mapping['ipc_section']}")
                lines.append(f"**Replace with**: {mapping['bns_section']}")
                lines.append(f"**Title**: {mapping['title']}")
                lines.append(f"**Original Text**: `{mapping['original_text']}`")
                lines.append("")
        
        # Critical issues
        critical_issues = report.get_critical_issues()
        if critical_issues:
            lines.append("## 🔴 Critical Issues")
            lines.append("")
            for issue in critical_issues:
                lines.append(f"### Line {issue.line_number}")
                lines.append(f"**Issue**: {issue.message}")
                lines.append(f"**Suggestion**: {issue.suggestion}")
                if issue.auto_fixable:
                    lines.append("✅ *Auto-fixable*")
                lines.append("")
        
        # Other issues by severity
        for severity in [SeverityLevel.HIGH, SeverityLevel.MEDIUM, SeverityLevel.LOW]:
            severity_issues = report.get_issues_by_severity(severity)
            if severity_issues:
                icon = {"high": "🟠", "medium": "🟡", "low": "🟢"}[severity.value]
                lines.append(f"## {icon} {severity.value.title()} Priority Issues")
                lines.append("")
                for issue in severity_issues:
                    lines.append(f"* **Line {issue.line_number}**: {issue.message}")
                    if issue.suggestion:
                        lines.append(f"  * Suggestion: {issue.suggestion}")
                lines.append("")
        
        # All citations list
        lines.append("## All Citations Found")
        lines.append("")
        for citation in report.citations:
            status_icon = {
                CitationStatus.VALID: "✅",
                CitationStatus.OUTDATED: "⚠️",
                CitationStatus.REPEALED: "❌",
                CitationStatus.UNKNOWN: "❓"
            }.get(citation.status, "")
            
            lines.append(f"* {status_icon} **Line {citation.line_number}**: `{citation.citation_text}`")
            if citation.replacement:
                lines.append(f"  * Replace with: {citation.replacement}")
        
        lines.append("")
        lines.append("---")
        lines.append("*Report generated by Nyaya-AI Document Audit Agent*")
        
        return "\n".join(lines)
    
    def apply_auto_fixes(self, document_text: str, report: AuditReport) -> str:
        """
        Automatically apply fixes for auto-fixable issues.
        
        Args:
            document_text: Original document text
            report: Audit report with identified issues
        
        Returns:
            Fixed document text
        """
        fixed_text = document_text
        
        # Get auto-fixable issues sorted by position (reverse order to maintain positions)
        auto_fixable = sorted(
            [i for i in report.get_auto_fixable_issues() if i.citation],
            key=lambda x: x.citation.position[0],
            reverse=True
        )
        
        for issue in auto_fixable:
            if issue.citation and issue.citation.replacement:
                # Replace IPC with BNS
                start, end = issue.citation.position
                lines = fixed_text.split('\n')
                
                if issue.citation.line_number <= len(lines):
                    line_idx = issue.citation.line_number - 1
                    line = lines[line_idx]
                    
                    # Replace IPC reference with BNS
                    old_ref = issue.citation.citation_text
                    new_ref = issue.citation.replacement
                    line = line.replace(old_ref, new_ref, 1)
                    lines[line_idx] = line
                    
                    fixed_text = '\n'.join(lines)
        
        return fixed_text


# ==================== Example Usage ====================

if __name__ == "__main__":
    # Sample legal document
    sample_doc = """
FIRST INFORMATION REPORT
Under Section 154 Cr.P.C.

The accused has committed offences under IPC 302, IPC 307, and IPC 420.
The case is similar to State v. Kumar (2015) where IPC 376 was invoked.

Further investigation revealed violations under IPC 498A and IPC 354.
The matter is governed by CrPC 156(3) and IPC 323.

Recent amendments under BNS 103 must be considered.
Reference: Sharma v. State (2020) 5 SCC 123
"""
    
    # Initialize agent
    agent = DocumentAuditAgent(strict_mode=True)
    
    # Audit document
    report = agent.audit_document(sample_doc, "FIR_Sample.txt")
    
    # Print report
    print(agent.export_markdown_report(report))
    
    print("\n" + "="*60)
    print("AUTO-FIX DEMONSTRATION")
    print("="*60 + "\n")
    
    # Apply auto-fixes
    fixed_doc = agent.apply_auto_fixes(sample_doc, report)
    print("FIXED DOCUMENT:")
    print(fixed_doc)
