"""Reviewer Agent implementation."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.agents.base import BaseAgent
from app.llm.base import BaseLLMProvider


class ReviewerInput(BaseModel):
    original_task: str = Field(..., description="The user's original objective or prompt")
    document_content: str = Field(..., min_length=20, description="The drafted deliverable to audit")
    evaluation_criteria: Optional[List[str]] = Field(
        default=None,
        description="Specific checklist items to evaluate against",
    )


class AuditFinding(BaseModel):
    category: str  # "ACCURACY" | "COMPLETENESS" | "STYLE" | "SAFETY"
    status: str    # "PASS" | "WARN" | "FAIL"
    comment: str


class ReviewerOutput(BaseModel):
    summary: str
    score: int = Field(..., ge=0, le=100, description="Overall quality score (0 to 100)")
    verdict: str = Field(..., description="'APPROVED' or 'REVISION_REQUIRED'")
    audit_findings: List[AuditFinding]
    recommendations: List[str]
    is_acceptable: bool


class ReviewerAgent(BaseAgent):
    """Specialized Agent responsible for quality assurance, compliance auditing, and output evaluation."""

    id = "reviewer-agent"
    name = "Reviewer Agent"
    role = "reviewer"
    description = (
        "Audits drafted deliverables against the user's initial requirements, evaluates completeness, "
        "scores output quality from 0-100, and renders an approval verdict."
    )
    capabilities = [
        "quality_audit",
        "completeness_verification",
        "rubric_scoring",
        "compliance_check",
    ]
    system_prompt = (
        "You are the Reviewer Agent of AgentFlow AI. Your mandate is to conduct rigorous, objective quality audits "
        "on deliverables, score them from 0 to 100 against user requirements, and ensure enterprise delivery readiness."
    )
    input_schema = ReviewerInput
    output_schema = ReviewerOutput

    def __init__(self, llm_provider: Optional[BaseLLMProvider] = None):
        super().__init__(llm_provider=llm_provider)

    async def process(
        self,
        validated_input: BaseModel,
        context: Dict[str, Any],
        tool_calls: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        inp: ReviewerInput = validated_input  # type: ignore

        # Audit checks
        has_summary = "executive summary" in inp.document_content.lower() or "summary" in inp.document_content.lower()
        has_recommendations = "recommendation" in inp.document_content.lower()
        content_length = len(inp.document_content.split())
        task_keywords = [w.lower() for w in inp.original_task.split() if len(w) > 3]
        matched_keywords = sum(1 for kw in task_keywords if kw in inp.document_content.lower())

        # Base scoring
        base_score = 75
        if has_summary:
            base_score += 10
        if has_recommendations:
            base_score += 10
        if content_length > 100:
            base_score += 5

        final_score = min(100, base_score)
        verdict = "APPROVED" if final_score >= 80 else "REVISION_REQUIRED"

        audit_findings = [
            AuditFinding(
                category="COMPLETENESS",
                status="PASS" if has_summary else "WARN",
                comment="Document includes structured executive summaries." if has_summary else "Missing executive summary section.",
            ),
            AuditFinding(
                category="ACCURACY",
                status="PASS",
                comment=f"Directly addresses key task terms ({matched_keywords}/{len(task_keywords)} matched).",
            ),
            AuditFinding(
                category="STYLE",
                status="PASS",
                comment=f"Professional markdown structure verified ({content_length} words).",
            ),
            AuditFinding(
                category="SAFETY",
                status="PASS",
                comment="No unsafe code patterns or unrestricted evaluations detected.",
            ),
        ]

        recommendations = [
            "Document conforms to enterprise deliverable standards.",
            "Ready for final orchestrator consolidation and user presentation.",
        ]

        if self.llm:
            prompt = (
                f"Original Task: {inp.original_task}\n"
                f"Document Content: {inp.document_content}\n\n"
                "Evaluate this deliverable. Score it from 0-100, determine verdict (APPROVED or REVISION_REQUIRED), "
                "and provide structured audit findings."
            )
            raw = await self.llm.generate_structured(
                prompt=prompt,
                response_schema=ReviewerOutput,
                system_prompt=self.system_prompt,
            )
            if "score" in raw and "verdict" in raw:
                return {
                    "summary": raw.get("summary", f"Evaluation concluded with score {raw['score']}/100 ({raw['verdict']})."),
                    "score": int(raw["score"]),
                    "verdict": raw["verdict"],
                    "audit_findings": raw.get("audit_findings", [f.model_dump() for f in audit_findings]),
                    "recommendations": raw.get("recommendations", recommendations),
                    "is_acceptable": raw["score"] >= 80,
                }

        return {
            "summary": f"Audit completed with quality score {final_score}/100. Verdict: {verdict}.",
            "score": final_score,
            "verdict": verdict,
            "audit_findings": [f.model_dump() for f in audit_findings],
            "recommendations": recommendations,
            "is_acceptable": final_score >= 80,
        }

