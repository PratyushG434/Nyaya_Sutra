"""Citation Tracer — Legal dependency chain mapper.

Maps the complete citation network for legal provisions and cases:
- Traces upstream dependencies (what this provision relies on)
- Traces downstream references (what cites this provision)
- Builds comprehensive citation graphs
- Identifies related provisions and precedents
- Detects circular dependencies
"""

from __future__ import annotations
import logging
from typing import Optional, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum

log = logging.getLogger(__name__)


# ==================== Data Models ====================

class CitationType(Enum):
    """Type of legal citation."""
    STATUTE = "statute"  # IPC, BNS, CrPC, etc.
    CASE_LAW = "case_law"  # Court judgments
    ARTICLE = "article"  # Constitutional articles
    RULE = "rule"  # Rules and regulations


class RelationType(Enum):
    """Type of relationship between citations."""
    CITES = "cites"  # A cites B
    CITED_BY = "cited_by"  # A is cited by B
    AMENDS = "amends"  # A amends B
    AMENDED_BY = "amended_by"  # A is amended by B
    OVERRULES = "overrules"  # A overrules B (case law)
    OVERRULED_BY = "overruled_by"  # A is overruled by B
    RELIES_ON = "relies_on"  # A relies on B
    RELIED_ON_BY = "relied_on_by"  # A is relied on by B
    INTERPRETS = "interprets"  # A interprets B
    INTERPRETED_BY = "interpreted_by"  # A is interpreted by B


@dataclass
class LegalCitation:
    """Represents a legal citation node."""
    citation_id: str  # e.g., "IPC_302", "BNS_103", "AIR_2020_SC_1234"
    citation_type: CitationType
    title: str
    full_text: str = ""
    year: Optional[int] = None
    metadata: dict = field(default_factory=dict)
    
    def __hash__(self):
        return hash(self.citation_id)
    
    def __eq__(self, other):
        if isinstance(other, LegalCitation):
            return self.citation_id == other.citation_id
        return False


@dataclass
class CitationRelation:
    """Represents a relationship between two citations."""
    source: LegalCitation
    target: LegalCitation
    relation_type: RelationType
    context: str = ""  # Context where relation was found
    strength: float = 1.0  # Relationship strength (0-1)


@dataclass
class CitationTrace:
    """Complete citation trace result."""
    root_citation: LegalCitation
    upstream_dependencies: list[CitationRelation]  # What root relies on
    downstream_references: list[CitationRelation]  # What cites root
    related_citations: list[LegalCitation]  # Related provisions
    depth_levels: dict[str, int]  # Citation ID -> depth from root
    total_citations: int
    circular_dependencies: list[tuple[str, str]]
    
    def get_citations_at_depth(self, depth: int) -> list[LegalCitation]:
        """Get all citations at a specific depth level."""
        citation_ids = [cid for cid, d in self.depth_levels.items() if d == depth]
        all_citations = (
            [self.root_citation] + 
            [r.target for r in self.upstream_dependencies] + 
            [r.target for r in self.downstream_references] +
            self.related_citations
        )
        return [c for c in all_citations if c.citation_id in citation_ids]
    
    def get_max_depth(self) -> int:
        """Get maximum depth in trace."""
        return max(self.depth_levels.values()) if self.depth_levels else 0


# ==================== Citation Database (Sample) ====================

# Sample citation database - in production, this would be a real database
CITATION_DATABASE = {
    "BNS_103": LegalCitation(
        citation_id="BNS_103",
        citation_type=CitationType.STATUTE,
        title="Punishment for murder",
        full_text="Whoever commits murder shall be punished with death or imprisonment for life..."
    ),
    "BNS_101": LegalCitation(
        citation_id="BNS_101",
        citation_type=CitationType.STATUTE,
        title="Culpable homicide",
        full_text="Whoever causes death by doing an act with the intention of causing death..."
    ),
    "BNS_100": LegalCitation(
        citation_id="BNS_100",
        citation_type=CitationType.STATUTE,
        title="Causing death",
        full_text="A person is said to cause death..."
    ),
    "IPC_302": LegalCitation(
        citation_id="IPC_302",
        citation_type=CitationType.STATUTE,
        title="Punishment for murder (Repealed)",
        full_text="[Repealed - See BNS 103]"
    ),
    "AIR_2020_SC_1234": LegalCitation(
        citation_id="AIR_2020_SC_1234",
        citation_type=CitationType.CASE_LAW,
        title="State v. Kumar",
        year=2020,
        full_text="Supreme Court judgment interpreting murder provisions..."
    ),
}

# Sample citation relationships
CITATION_RELATIONS = [
    # BNS 103 relies on BNS 101 (culpable homicide definition)
    CitationRelation(
        source=CITATION_DATABASE["BNS_103"],
        target=CITATION_DATABASE["BNS_101"],
        relation_type=RelationType.RELIES_ON,
        context="Murder is defined as culpable homicide under certain circumstances",
        strength=0.9
    ),
    # BNS 101 relies on BNS 100 (causing death definition)
    CitationRelation(
        source=CITATION_DATABASE["BNS_101"],
        target=CITATION_DATABASE["BNS_100"],
        relation_type=RelationType.RELIES_ON,
        context="Culpable homicide requires causing death",
        strength=0.95
    ),
    # Case law cites BNS 103
    CitationRelation(
        source=CITATION_DATABASE["AIR_2020_SC_1234"],
        target=CITATION_DATABASE["BNS_103"],
        relation_type=RelationType.INTERPRETS,
        context="Supreme Court interpretation of murder provisions",
        strength=0.85
    ),
    # BNS 103 replaces IPC 302
    CitationRelation(
        source=CITATION_DATABASE["BNS_103"],
        target=CITATION_DATABASE["IPC_302"],
        relation_type=RelationType.AMENDS,
        context="BNS replaced IPC in 2024",
        strength=1.0
    ),
]


# ==================== Citation Tracer Agent ====================

class CitationTracerAgent:
    """Agent for tracing legal citation dependencies."""
    
    def __init__(
        self,
        citation_db: Optional[dict[str, LegalCitation]] = None,
        relation_db: Optional[list[CitationRelation]] = None,
        max_depth: int = 5,
        search_provider: Optional[Callable] = None
    ):
        """
        Initialize citation tracer.
        
        Args:
            citation_db: Database of citations (defaults to sample)
            relation_db: Database of relations (defaults to sample)
            max_depth: Maximum depth for trace traversal
            search_provider: Optional function to search for citations
        """
        self.citation_db = citation_db or CITATION_DATABASE
        self.relation_db = relation_db or CITATION_RELATIONS
        self.max_depth = max_depth
        self.search_provider = search_provider
        
        # Build adjacency lists for efficient traversal
        self._build_graph()
    
    def _build_graph(self):
        """Build adjacency lists from relations."""
        self.upstream_graph = defaultdict(list)  # What this cites
        self.downstream_graph = defaultdict(list)  # What cites this
        
        for relation in self.relation_db:
            source_id = relation.source.citation_id
            target_id = relation.target.citation_id
            
            # Map relation types to graph directions
            if relation.relation_type in [
                RelationType.RELIES_ON,
                RelationType.CITES,
                RelationType.AMENDS,
                RelationType.INTERPRETS
            ]:
                self.upstream_graph[source_id].append(relation)
            
            if relation.relation_type in [
                RelationType.RELIED_ON_BY,
                RelationType.CITED_BY,
                RelationType.AMENDED_BY,
                RelationType.INTERPRETED_BY
            ]:
                self.downstream_graph[source_id].append(relation)
            
            # Add reverse relations
            reverse_type = self._get_reverse_relation(relation.relation_type)
            if reverse_type:
                reverse_rel = CitationRelation(
                    source=relation.target,
                    target=relation.source,
                    relation_type=reverse_type,
                    context=relation.context,
                    strength=relation.strength
                )
                
                if reverse_type in [
                    RelationType.RELIED_ON_BY,
                    RelationType.CITED_BY,
                    RelationType.AMENDED_BY,
                    RelationType.INTERPRETED_BY
                ]:
                    self.downstream_graph[target_id].append(reverse_rel)
    
    def _get_reverse_relation(self, rel_type: RelationType) -> Optional[RelationType]:
        """Get reverse relation type."""
        reverse_map = {
            RelationType.CITES: RelationType.CITED_BY,
            RelationType.CITED_BY: RelationType.CITES,
            RelationType.RELIES_ON: RelationType.RELIED_ON_BY,
            RelationType.RELIED_ON_BY: RelationType.RELIES_ON,
            RelationType.AMENDS: RelationType.AMENDED_BY,
            RelationType.AMENDED_BY: RelationType.AMENDS,
            RelationType.INTERPRETS: RelationType.INTERPRETED_BY,
            RelationType.INTERPRETED_BY: RelationType.INTERPRETS,
            RelationType.OVERRULES: RelationType.OVERRULED_BY,
            RelationType.OVERRULED_BY: RelationType.OVERRULES,
        }
        return reverse_map.get(rel_type)
    
    def trace_citation(
        self,
        citation_id: str,
        include_upstream: bool = True,
        include_downstream: bool = True,
        max_depth: Optional[int] = None
    ) -> CitationTrace:
        """
        Trace complete dependency chain for a citation.
        
        Args:
            citation_id: ID of citation to trace (e.g., "BNS_103")
            include_upstream: Include upstream dependencies
            include_downstream: Include downstream references
            max_depth: Override default max depth
        
        Returns:
            Complete citation trace
        """
        if citation_id not in self.citation_db:
            log.error(f"Citation {citation_id} not found in database")
            raise ValueError(f"Citation not found: {citation_id}")
        
        root = self.citation_db[citation_id]
        max_depth = max_depth or self.max_depth
        
        log.info(f"Tracing citation: {citation_id} (max_depth={max_depth})")
        
        # Trace upstream and downstream
        upstream_rels, upstream_depths = self._trace_direction(
            citation_id, self.upstream_graph, max_depth
        ) if include_upstream else ([], {})
        
        downstream_rels, downstream_depths = self._trace_direction(
            citation_id, self.downstream_graph, max_depth
        ) if include_downstream else ([], {})
        
        # Merge depth levels
        depth_levels = {citation_id: 0}
        depth_levels.update(upstream_depths)
        depth_levels.update(downstream_depths)
        
        # Find related citations (same topic, similar provisions)
        related = self._find_related_citations(root)
        
        # Detect circular dependencies
        circular = self._detect_circular_deps(citation_id)
        
        trace = CitationTrace(
            root_citation=root,
            upstream_dependencies=upstream_rels,
            downstream_references=downstream_rels,
            related_citations=related,
            depth_levels=depth_levels,
            total_citations=len(depth_levels),
            circular_dependencies=circular
        )
        
        log.info(f"Trace complete: {trace.total_citations} citations, "
                f"{len(upstream_rels)} upstream, {len(downstream_rels)} downstream")
        
        return trace
    
    def _trace_direction(
        self,
        start_id: str,
        graph: dict,
        max_depth: int
    ) -> tuple[list[CitationRelation], dict[str, int]]:
        """
        Trace in one direction (upstream or downstream) using BFS.
        
        Returns:
            (list of relations, dict of citation_id -> depth)
        """
        relations = []
        depths = {}
        visited = {start_id}
        queue = deque([(start_id, 0)])
        
        while queue:
            current_id, depth = queue.popleft()
            
            if depth >= max_depth:
                continue
            
            for relation in graph.get(current_id, []):
                target_id = relation.target.citation_id
                
                if target_id not in visited:
                    visited.add(target_id)
                    relations.append(relation)
                    depths[target_id] = depth + 1
                    queue.append((target_id, depth + 1))
        
        return relations, depths
    
    def _find_related_citations(self, citation: LegalCitation) -> list[LegalCitation]:
        """Find related citations (same statute, similar topic)."""
        related = []
        
        # Extract statute prefix (e.g., "BNS" from "BNS_103")
        parts = citation.citation_id.split('_')
        if len(parts) > 1:
            statute_prefix = parts[0]
            
            # Find other citations from same statute
            for cid, cite in self.citation_db.items():
                if cid != citation.citation_id and cid.startswith(statute_prefix):
                    # Check if section numbers are close
                    try:
                        root_num = int(parts[1])
                        cite_num = int(cid.split('_')[1])
                        if abs(root_num - cite_num) <= 5:  # Within 5 sections
                            related.append(cite)
                    except (ValueError, IndexError):
                        pass
        
        return related[:10]  # Limit to 10 related
    
    def _detect_circular_deps(self, start_id: str) -> list[tuple[str, str]]:
        """Detect circular dependencies in citation graph."""
        circular = []
        visited = set()
        rec_stack = set()
        
        def dfs(node_id: str, path: list[str]):
            visited.add(node_id)
            rec_stack.add(node_id)
            path.append(node_id)
            
            for relation in self.upstream_graph.get(node_id, []):
                target_id = relation.target.citation_id
                
                if target_id not in visited:
                    dfs(target_id, path.copy())
                elif target_id in rec_stack:
                    # Found cycle
                    cycle_start = path.index(target_id)
                    cycle = path[cycle_start:] + [target_id]
                    for i in range(len(cycle) - 1):
                        circular.append((cycle[i], cycle[i+1]))
            
            rec_stack.remove(node_id)
        
        dfs(start_id, [])
        return circular
    
    def export_trace_markdown(self, trace: CitationTrace) -> str:
        """Export trace as formatted markdown."""
        lines = [
            f"# Citation Trace: {trace.root_citation.title}",
            f"**Citation ID**: `{trace.root_citation.citation_id}`",
            f"**Type**: {trace.root_citation.citation_type.value}",
            "",
            f"**Total Citations in Network**: {trace.total_citations}",
            f"**Max Depth**: {trace.get_max_depth()}",
            "",
            "---",
            ""
        ]
        
        # Upstream dependencies
        if trace.upstream_dependencies:
            lines.append("## ⬆️ Upstream Dependencies")
            lines.append("*What this provision relies on*")
            lines.append("")
            
            for rel in trace.upstream_dependencies:
                depth = trace.depth_levels.get(rel.target.citation_id, 0)
                indent = "  " * depth
                lines.append(f"{indent}* **{rel.target.citation_id}**: {rel.target.title}")
                lines.append(f"{indent}  * Relation: {rel.relation_type.value}")
                if rel.context:
                    lines.append(f"{indent}  * Context: {rel.context}")
            lines.append("")
        
        # Downstream references
        if trace.downstream_references:
            lines.append("## ⬇️ Downstream References")
            lines.append("*What cites this provision*")
            lines.append("")
            
            for rel in trace.downstream_references:
                depth = trace.depth_levels.get(rel.target.citation_id, 0)
                indent = "  " * depth
                lines.append(f"{indent}* **{rel.target.citation_id}**: {rel.target.title}")
                lines.append(f"{indent}  * Relation: {rel.relation_type.value}")
                if rel.context:
                    lines.append(f"{indent}  * Context: {rel.context}")
            lines.append("")
        
        # Related citations
        if trace.related_citations:
            lines.append("## 🔗 Related Provisions")
            lines.append("")
            for cite in trace.related_citations:
                lines.append(f"* **{cite.citation_id}**: {cite.title}")
            lines.append("")
        
        # Circular dependencies warning
        if trace.circular_dependencies:
            lines.append("## ⚠️ Circular Dependencies Detected")
            lines.append("")
            for source, target in trace.circular_dependencies:
                lines.append(f"* {source} → {target}")
            lines.append("")
        
        lines.append("---")
        lines.append("*Trace generated by Nyaya-AI Citation Tracer*")
        
        return "\n".join(lines)
    
    def export_trace_graph(self, trace: CitationTrace) -> dict:
        """Export trace as graph structure (for visualization)."""
        nodes = []
        edges = []
        
        # Root node
        nodes.append({
            "id": trace.root_citation.citation_id,
            "label": trace.root_citation.title,
            "type": trace.root_citation.citation_type.value,
            "depth": 0,
            "is_root": True
        })
        
        # Upstream nodes and edges
        for rel in trace.upstream_dependencies:
            nodes.append({
                "id": rel.target.citation_id,
                "label": rel.target.title,
                "type": rel.target.citation_type.value,
                "depth": trace.depth_levels.get(rel.target.citation_id, 0)
            })
            edges.append({
                "source": rel.source.citation_id,
                "target": rel.target.citation_id,
                "type": rel.relation_type.value,
                "strength": rel.strength
            })
        
        # Downstream nodes and edges
        for rel in trace.downstream_references:
            nodes.append({
                "id": rel.target.citation_id,
                "label": rel.target.title,
                "type": rel.target.citation_type.value,
                "depth": trace.depth_levels.get(rel.target.citation_id, 0)
            })
            edges.append({
                "source": rel.source.citation_id,
                "target": rel.target.citation_id,
                "type": rel.relation_type.value,
                "strength": rel.strength
            })
        
        return {
            "nodes": nodes,
            "edges": edges,
            "root": trace.root_citation.citation_id
        }


# ==================== Example Usage ====================

if __name__ == "__main__":
    # Initialize tracer
    tracer = CitationTracerAgent(max_depth=3)
    
    # Trace BNS Section 103 (Murder)
    trace = tracer.trace_citation("BNS_103")
    
    # Print markdown report
    print(tracer.export_trace_markdown(trace))
    
    print("\n" + "="*60)
    print("GRAPH STRUCTURE")
    print("="*60 + "\n")
    
    # Export graph structure
    import json
    graph = tracer.export_trace_graph(trace)
    print(json.dumps(graph, indent=2))
