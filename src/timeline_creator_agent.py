from __future__ import annotations
import json
import logging
import hashlib
from typing import Optional, Literal, Callable, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum

log = logging.getLogger(__name__)



class StepStatus(Enum):
    """Step completion status."""
    UPCOMING = "upcoming"
    CURRENT = "current"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


class TimelineType(Enum):
    """Common legal timeline types."""
    CONSUMER_COMPLAINT = "consumer_complaint"
    PROPERTY_DISPUTE = "property_dispute"
    EMPLOYMENT_ISSUE = "employment_issue"
    FAMILY_MATTER = "family_matter"
    POLICE_COMPLAINT = "police_complaint"
    RTI_APPLICATION = "rti_application"
    CIVIL_SUIT = "civil_suit"
    BAIL_APPLICATION = "bail_application"
    CUSTOM = "custom"


@dataclass
class TimelineStep:
    """Represents a single step in the legal process timeline."""
    step: int
    title: str
    description: str
    status: StepStatus = StepStatus.UPCOMING
    where_to_go: str = ""
    documents_needed: list[str] = field(default_factory=list)
    expected_duration: str = ""
    estimated_cost: str = ""
    related_links: list[str] = field(default_factory=list)
    prerequisites: list[int] = field(default_factory=list)
    alternatives: list[TimelineStep] = field(default_factory=list)
    notes: str = ""
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary, handling enums and datetime."""
        data = asdict(self)
        data["status"] = self.status.value
        if self.completed_at:
            data["completed_at"] = self.completed_at.isoformat()
        return data
    
    def mark_done(self) -> None:
        """Mark step as completed."""
        self.status = StepStatus.DONE
        self.completed_at = datetime.now()
    
    def is_blocked(self, completed_steps: set[int]) -> bool:
        """Check if step is blocked by incomplete prerequisites."""
        return bool(self.prerequisites and not all(p in completed_steps for p in self.prerequisites))


@dataclass
class Timeline:
    """Represents a complete legal process timeline."""
    case_type: str
    summary: str
    timeline: list[TimelineStep]
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    estimated_total_cost: str = ""
    estimated_total_duration: str = ""
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "case_type": self.case_type,
            "summary": self.summary,
            "timeline": [step.to_dict() for step in self.timeline],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
            "tags": self.tags,
            "estimated_total_cost": self.estimated_total_cost,
            "estimated_total_duration": self.estimated_total_duration,
        }
    
    def get_step(self, step_num: int) -> Optional[TimelineStep]:
        """Get step by number."""
        for step in self.timeline:
            if step.step == step_num:
                return step
        return None
    
    def get_current_steps(self) -> list[TimelineStep]:
        """Get all current/in-progress steps."""
        return [s for s in self.timeline if s.status in (StepStatus.CURRENT, StepStatus.IN_PROGRESS)]
    
    def get_progress_percentage(self) -> float:
        """Calculate completion percentage."""
        if not self.timeline:
            return 0.0
        done_count = sum(1 for s in self.timeline if s.status == StepStatus.DONE)
        return (done_count / len(self.timeline)) * 100
    
    def get_next_actionable_steps(self) -> list[TimelineStep]:
        """Get steps that can be started now (not blocked)."""
        completed = {s.step for s in self.timeline if s.status == StepStatus.DONE}
        return [
            s for s in self.timeline
            if s.status == StepStatus.UPCOMING and not s.is_blocked(completed)
        ]


TIMELINE_TEMPLATES = {
    TimelineType.CONSUMER_COMPLAINT: {
        "case_type": "Consumer Complaint",
        "steps": [
            {
                "step": 1, "title": "Gather Evidence",
                "description": "Collect all bills, receipts, warranty cards, communication records",
                "where_to_go": "Your records at home",
                "documents_needed": ["Purchase bill", "Product warranty", "Communication emails/SMS"],
                "expected_duration": "1-2 days",
                "estimated_cost": "₹0"
            },
            {
                "step": 2, "title": "Send Legal Notice",
                "description": "Send a formal complaint to the seller/service provider",
                "where_to_go": "Registered post or email",
                "documents_needed": ["Copy of bill", "Defect description"],
                "expected_duration": "1 week",
                "estimated_cost": "₹100-500"
            },
            {
                "step": 3, "title": "File Consumer Complaint",
                "description": "If no response, file complaint at District Consumer Forum",
                "where_to_go": "District Consumer Disputes Redressal Forum",
                "documents_needed": ["Legal notice copy", "All evidence", "Complaint form"],
                "expected_duration": "1 day for filing",
                "estimated_cost": "₹500-1000 (court fee)"
            },
        ]
    },
    TimelineType.RTI_APPLICATION: {
        "case_type": "RTI Application",
        "steps": [
            {
                "step": 1, "title": "Identify Information Needed",
                "description": "Clearly define what information you need and from which department",
                "where_to_go": "Self-assessment",
                "documents_needed": [],
                "expected_duration": "1 day",
                "estimated_cost": "₹0"
            },
            {
                "step": 2, "title": "Draft RTI Application",
                "description": "Write application with specific questions, pay ₹10 fee",
                "where_to_go": "Online RTI portal or department office",
                "documents_needed": ["Application draft", "DD/Cash for ₹10"],
                "expected_duration": "1-2 days",
                "estimated_cost": "₹10"
            },
            {
                "step": 3, "title": "Submit Application",
                "description": "Submit to Public Information Officer of concerned department",
                "where_to_go": "Department office or online portal",
                "documents_needed": ["RTI application", "Fee payment proof"],
                "expected_duration": "1 day",
                "estimated_cost": "₹0"
            },
            {
                "step": 4, "title": "Await Response",
                "description": "PIO must respond within 30 days (48 hours for life/liberty)",
                "where_to_go": "Wait for postal/email response",
                "documents_needed": [],
                "expected_duration": "30 days",
                "estimated_cost": "₹0"
            },
        ]
    },
}



class TimelineCreatorAgent:    
    def __init__(
        self,
        llm_provider: Optional[Callable] = None,
        cache_enabled: bool = True,
        validation_strict: bool = True,
        event_callbacks: Optional[dict[str, Callable]] = None
    ):
        """
        Initialize the timeline creator agent.
        
        Args:
            llm_provider: Function to call LLM (signature: (messages, temperature) -> dict)
            cache_enabled: Enable caching of generated timelines
            validation_strict: Strict validation mode (fail on invalid timelines)
            event_callbacks: Optional callbacks for events (on_create, on_update, on_complete)
        """
        self.llm_provider = llm_provider
        self.cache_enabled = cache_enabled
        self.validation_strict = validation_strict
        self.event_callbacks = event_callbacks or {}
        self._cache: dict[str, Timeline] = {}
    
    def _get_cache_key(self, situation: str, legal_context: str) -> str:
        """Generate cache key from inputs."""
        content = f"{situation}|{legal_context}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _trigger_event(self, event_name: str, **kwargs) -> None:
        """Trigger event callback if registered."""
        if event_name in self.event_callbacks:
            try:
                self.event_callbacks[event_name](**kwargs)
            except Exception as e:
                log.warning(f"Event callback {event_name} failed: {e}")
    
    def _validate_timeline(self, timeline_data: dict) -> tuple[bool, list[str]]:
        """
        Validate timeline structure and content.
        
        Returns:
            (is_valid, list of error messages)
        """
        errors = []
        
        if "timeline" not in timeline_data:
            errors.append("Missing 'timeline' field")
            return False, errors
        
        if not isinstance(timeline_data["timeline"], list):
            errors.append("'timeline' must be a list")
            return False, errors
        
        steps = timeline_data["timeline"]
        if not steps:
            errors.append("Timeline must have at least one step")
        
        step_numbers = set()
        for i, step in enumerate(steps):
            # Check required fields
            for field in ["step", "title", "description"]:
                if field not in step:
                    errors.append(f"Step {i+1}: Missing required field '{field}'")
            
            # Check step numbering
            step_num = step.get("step")
            if step_num in step_numbers:
                errors.append(f"Duplicate step number: {step_num}")
            step_numbers.add(step_num)
            
            # Check status validity
            status = step.get("status", "upcoming")
            if status not in [s.value for s in StepStatus]:
                errors.append(f"Step {step_num}: Invalid status '{status}'")
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    def generate_from_template(
        self,
        timeline_type: TimelineType,
        customize: Optional[dict] = None
    ) -> Timeline:
        """
        Generate timeline from a predefined template.
        
        Args:
            timeline_type: Type of legal timeline to generate
            customize: Optional dict to customize template fields
        
        Returns:
            Generated Timeline object
        """
        if timeline_type not in TIMELINE_TEMPLATES:
            raise ValueError(f"No template found for {timeline_type}")
        
        template = TIMELINE_TEMPLATES[timeline_type].copy()
        if customize:
            template.update(customize)
        
        steps = [
            TimelineStep(
                step=s["step"],
                title=s["title"],
                description=s["description"],
                where_to_go=s.get("where_to_go", ""),
                documents_needed=s.get("documents_needed", []),
                expected_duration=s.get("expected_duration", ""),
                estimated_cost=s.get("estimated_cost", ""),
                status=StepStatus.CURRENT if s["step"] == 1 else StepStatus.UPCOMING
            )
            for s in template["steps"]
        ]
        
        timeline = Timeline(
            case_type=template["case_type"],
            summary=template.get("summary", f"Process for {template['case_type']}"),
            timeline=steps
        )
        
        self._trigger_event("on_create", timeline=timeline)
        return timeline
    
    def generate_timeline(
        self,
        situation: str,
        legal_context: str = "",
        use_cache: bool = True
    ) -> Timeline:
        """
        Generate a legal process timeline using LLM.
        
        Args:
            situation: Description of the citizen's legal issue
            legal_context: Optional additional legal context from RAG
            use_cache: Use cached result if available
        
        Returns:
            Generated Timeline object
        """
        # Check cache
        if self.cache_enabled and use_cache:
            cache_key = self._get_cache_key(situation, legal_context)
            if cache_key in self._cache:
                log.info("Returning cached timeline")
                return self._cache[cache_key]
        
        if not self.llm_provider:
            log.warning("No LLM provider configured, using fallback")
            return self._generate_fallback_timeline(situation)
        
        # Prepare prompt
        system_prompt = self._build_system_prompt()
        user_msg = f"SITUATION: {situation}"
        if legal_context:
            user_msg += f"\n\nRELEVANT LAW:\n{legal_context[:2000]}"
        
        try:
            # Call LLM
            response = self.llm_provider(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.2
            )
            
            # Validate response
            is_valid, errors = self._validate_timeline(response)
            if not is_valid:
                log.error(f"Timeline validation failed: {errors}")
                if self.validation_strict:
                    raise ValueError(f"Invalid timeline: {errors}")
                return self._generate_fallback_timeline(situation)
            
            # Convert to Timeline object
            timeline = self._dict_to_timeline(response)
            
            # Cache result
            if self.cache_enabled:
                cache_key = self._get_cache_key(situation, legal_context)
                self._cache[cache_key] = timeline
            
            self._trigger_event("on_create", timeline=timeline)
            return timeline
            
        except Exception as e:
            log.error(f"Timeline generation failed: {e}", exc_info=True)
            return self._generate_fallback_timeline(situation)
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt for LLM."""
        return """\
You are a legal process advisor for Indian citizens. Generate a detailed step-by-step timeline as valid JSON.

RULES:
- Generate 4-10 steps covering the complete legal process
- Each step must have: step (int), title (str), description (str), status (str: "upcoming"),
  where_to_go (str), documents_needed (list[str]), expected_duration (str)
- Set step 1 status to "current" (the first action)
- Use simple, non-technical language
- Include practical details: which office, what documents, how long, how much
- Be specific to Indian legal procedures
- Add estimated costs where applicable (₹ format)

Return ONLY valid JSON in this exact format:
{
  "case_type": "...",
  "summary": "Brief 1-line summary",
  "estimated_total_duration": "...",
  "timeline": [
    {
      "step": 1,
      "title": "...",
      "description": "...",
      "where_to_go": "...",
      "documents_needed": ["..."],
      "expected_duration": "...",
      "status": "current"
    }
  ]
}"""
    
    def _dict_to_timeline(self, data: dict) -> Timeline:
        """Convert dictionary to Timeline object."""
        steps = [
            TimelineStep(
                step=s["step"],
                title=s["title"],
                description=s["description"],
                status=StepStatus(s.get("status", "upcoming")),
                where_to_go=s.get("where_to_go", ""),
                documents_needed=s.get("documents_needed", []),
                expected_duration=s.get("expected_duration", ""),
                estimated_cost=s.get("estimated_cost", ""),
                related_links=s.get("related_links", []),
                notes=s.get("notes", "")
            )
            for s in data["timeline"]
        ]
        
        return Timeline(
            case_type=data.get("case_type", "Legal Process"),
            summary=data.get("summary", ""),
            timeline=steps,
            estimated_total_cost=data.get("estimated_total_cost", ""),
            estimated_total_duration=data.get("estimated_total_duration", "")
        )
    
    def _generate_fallback_timeline(self, situation: str) -> Timeline:
        """Generate a basic fallback timeline when LLM fails."""
        return Timeline(
            case_type="Legal Process",
            summary=f"Process for: {situation[:100]}",
            timeline=[
                TimelineStep(
                    step=1,
                    title="Gather Information",
                    description="Collect all relevant documents and facts about your situation",
                    status=StepStatus.CURRENT,
                    expected_duration="1-2 days"
                ),
                TimelineStep(
                    step=2,
                    title="Consult Legal Expert",
                    description="Speak with a lawyer or legal aid clinic for specific guidance",
                    where_to_go="District Legal Services Authority or lawyer's office",
                    expected_duration="1 week"
                ),
            ]
        )
    
    def update_step_status(
        self,
        timeline: Timeline,
        step_num: int,
        new_status: StepStatus,
        auto_advance: bool = True
    ) -> Timeline:
        """
        Update a step's status and optionally auto-advance to next step.
        
        Args:
            timeline: Timeline to update
            step_num: Step number to update
            new_status: New status for the step
            auto_advance: Automatically set next step to CURRENT when marking DONE
        
        Returns:
            Updated timeline
        """
        step = timeline.get_step(step_num)
        if not step:
            raise ValueError(f"Step {step_num} not found")
        
        old_status = step.status
        step.status = new_status
        
        if new_status == StepStatus.DONE:
            step.mark_done()
            
            # Auto-advance to next step
            if auto_advance:
                next_steps = timeline.get_next_actionable_steps()
                if next_steps:
                    next_steps[0].status = StepStatus.CURRENT
        
        timeline.updated_at = datetime.now()
        
        self._trigger_event(
            "on_update",
            timeline=timeline,
            step_num=step_num,
            old_status=old_status,
            new_status=new_status
        )
        
        # Check if timeline is complete
        if all(s.status == StepStatus.DONE for s in timeline.timeline):
            self._trigger_event("on_complete", timeline=timeline)
        
        return timeline
    
    def export_json(self, timeline: Timeline) -> str:
        """Export timeline as JSON string."""
        return json.dumps(timeline.to_dict(), indent=2, ensure_ascii=False)
    
    def export_markdown(self, timeline: Timeline, include_metadata: bool = True) -> str:
        """Export timeline as formatted markdown."""
        lines = []
        
        # Header
        lines.append(f"# 🕒 {timeline.case_type}")
        lines.append(f"_{timeline.summary}_\n")
        
        if include_metadata:
            lines.append(f"**Progress**: {timeline.get_progress_percentage():.0f}% complete")
            if timeline.estimated_total_duration:
                lines.append(f"**Total Duration**: {timeline.estimated_total_duration}")
            if timeline.estimated_total_cost:
                lines.append(f"**Total Cost**: {timeline.estimated_total_cost}")
            lines.append("")
        
        lines.append("---\n")
        
        # Steps
        for step in timeline.timeline:
            icon = {
                StepStatus.DONE: "✅",
                StepStatus.CURRENT: "👉",
                StepStatus.IN_PROGRESS: "⏳",
                StepStatus.BLOCKED: "🚫",
                StepStatus.SKIPPED: "⏭️",
                StepStatus.UPCOMING: "⬜",
            }[step.status]
            
            title_fmt = f"~~{step.title}~~" if step.status == StepStatus.DONE else step.title
            lines.append(f"\n{icon} **Step {step.step}**: {title_fmt}")
            
            if step.status != StepStatus.DONE:
                lines.append(f"   {step.description}")
                if step.where_to_go:
                    lines.append(f"   📍 **Where**: {step.where_to_go}")
                if step.documents_needed:
                    lines.append(f"   📄 **Documents**: {', '.join(step.documents_needed)}")
                if step.expected_duration:
                    lines.append(f"   ⏱️ **Duration**: {step.expected_duration}")
                if step.estimated_cost:
                    lines.append(f"   💰 **Cost**: {step.estimated_cost}")
                if step.notes:
                    lines.append(f"   📝 **Notes**: {step.notes}")
        
        lines.append("\n---")
        lines.append("_This timeline is for guidance only. Consult a lawyer for case-specific advice._")
        
        return "\n".join(lines)
    
    def export_html(self, timeline: Timeline) -> str:
        """Export timeline as HTML."""
        progress = timeline.get_progress_percentage()
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{timeline.case_type}</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 20px auto; padding: 0 20px; }}
        .header {{ border-bottom: 2px solid #333; padding-bottom: 10px; margin-bottom: 20px; }}
        .progress {{ background: #f0f0f0; height: 20px; border-radius: 10px; margin: 20px 0; }}
        .progress-bar {{ background: #4CAF50; height: 100%; border-radius: 10px; width: {progress}%; }}
        .step {{ margin: 20px 0; padding: 15px; border-left: 4px solid #ddd; background: #f9f9f9; }}
        .step.done {{ border-left-color: #4CAF50; opacity: 0.7; }}
        .step.current {{ border-left-color: #2196F3; background: #e3f2fd; }}
        .step-title {{ font-weight: bold; font-size: 1.1em; }}
        .step-details {{ margin-top: 10px; }}
        .detail {{ margin: 5px 0; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🕒 {timeline.case_type}</h1>
        <p><em>{timeline.summary}</em></p>
        <div class="progress"><div class="progress-bar"></div></div>
        <p><strong>Progress:</strong> {progress:.0f}% complete</p>
    </div>
    <div class="steps">
"""
        
        for step in timeline.timeline:
            status_class = step.status.value.replace("_", "-")
            icon = {"done": "✅", "current": "👉", "in_progress": "⏳", "blocked": "🚫", "upcoming": "⬜"}
            
            html += f'        <div class="step {status_class}">\n'
            html += f'            <div class="step-title">{icon.get(step.status.value, "⬜")} Step {step.step}: {step.title}</div>\n'
            html += f'            <div class="step-details">\n'
            html += f'                <div class="detail">{step.description}</div>\n'
            
            if step.where_to_go:
                html += f'                <div class="detail">📍 <strong>Where:</strong> {step.where_to_go}</div>\n'
            if step.documents_needed:
                html += f'                <div class="detail">📄 <strong>Documents:</strong> {", ".join(step.documents_needed)}</div>\n'
            if step.expected_duration:
                html += f'                <div class="detail">⏱️ <strong>Duration:</strong> {step.expected_duration}</div>\n'
            if step.estimated_cost:
                html += f'                <div class="detail">💰 <strong>Cost:</strong> {step.estimated_cost}</div>\n'
            
            html += '            </div>\n'
            html += '        </div>\n'
        
        html += """
    </div>
    <p><em>This timeline is for guidance only. Consult a lawyer for case-specific advice.</em></p>
</body>
</html>
"""
        return html



if __name__ == "__main__":
    # Initialize agent
    agent = TimelineCreatorAgent(
        cache_enabled=True,
        event_callbacks={
            "on_create": lambda **kw: print(f"✨ Timeline created: {kw['timeline'].case_type}"),
            "on_update": lambda **kw: print(f"📝 Step {kw['step_num']} updated"),
            "on_complete": lambda **kw: print("🎉 Timeline completed!"),
        }
    )
    
    # Generate from template
    timeline = agent.generate_from_template(TimelineType.RTI_APPLICATION)
    print(agent.export_markdown(timeline))
    
    # Update step status
    agent.update_step_status(timeline, 1, StepStatus.DONE)
    
    # Export to different formats
    print("\n--- JSON Export ---")
    print(agent.export_json(timeline))
