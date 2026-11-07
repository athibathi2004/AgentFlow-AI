"""Writer Agent implementation."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.agents.base import BaseAgent
from app.llm.base import BaseLLMProvider


class WriterInput(BaseModel):
    title: Optional[str] = Field(default=None, description="Requested document title")
    research_summary: Optional[str] = Field(default="", description="Findings from research stage")
    analysis_insights: List[str] = Field(default_factory=list, description="Strategic insights from analyst")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Quantitative metrics to include")
    original_task: Optional[str] = Field(default="", description="Original user prompt or requirements")


class ReportSection(BaseModel):
    heading: str
    body: str


class WriterOutput(BaseModel):
    title: str
    summary: str
    markdown_content: str
    sections: List[ReportSection]
    word_count: int


class WriterAgent(BaseAgent):
    """Specialized Agent responsible for document drafting, synthesis, and technical report generation."""

    id = "writer-agent"
    name = "Writer Agent"
    role = "writer"
    description = (
        "Synthesizes research findings, quantitative metrics, and architectural insights "
        "into comprehensive, publication-ready technical reports."
    )
    capabilities = [
        "technical_writing",
        "document_synthesis",
        "markdown_formatting",
        "executive_reporting",
    ]
    system_prompt = (
        "You are the Writer Agent of AgentFlow AI. Your mandate is to synthesize complex multi-agent outputs "
        "into articulate, structured, professional technical deliverables formatted in clean Markdown."
    )
    input_schema = WriterInput
    output_schema = WriterOutput

    def __init__(self, llm_provider: Optional[BaseLLMProvider] = None):
        super().__init__(llm_provider=llm_provider)

    async def process(
        self,
        validated_input: BaseModel,
        context: Dict[str, Any],
        tool_calls: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        inp: WriterInput = validated_input  # type: ignore

        title = inp.title or "Enterprise Technical Report"
        if inp.original_task and not inp.title:
            title = f"Technical Report: {inp.original_task[:60]}"

        insights_text = "\n".join([f"- {i}" for i in inp.analysis_insights]) or "- Robust multi-agent collaboration."
        metrics_text = "\n".join([f"- **{k}**: {v}" for k, v in inp.metrics.items()]) or "- Standard metrics verified."

        # Optionally invoke summarizer tool on raw input if lengthy
        summary_call = await self.call_tool(
            tool_id="summarizer",
            parameters={
                "text": (
                    f"AgentFlow AI multi-agent execution pipeline. "
                    f"User objective: {inp.original_task or 'Technical evaluation'}. "
                    f"Research findings: {inp.research_summary or 'Analyzed industry benchmarks and patterns'}. "
                    f"Analysis highlights include verified metrics and mitigation strategies."
                ),
                "max_bullets": 2,
            },
            recorded_calls=tool_calls,
        )
        executive_summary = summary_call.get("executive_summary", "Comprehensive multi-agent technical evaluation.")

        sections = [
            ReportSection(
                heading="1. Executive Summary",
                body=executive_summary,
            ),
            ReportSection(
                heading="2. Research Findings",
                body=inp.research_summary or "Empirical investigation reveals rapid maturation of agent workflows.",
            ),
            ReportSection(
                heading="3. Quantitative & Strategic Analysis",
                body=f"Key analytical insights:\n{insights_text}\n\nQuantitative Metrics:\n{metrics_text}",
            ),
            ReportSection(
                heading="4. Architectural Recommendations",
                body=(
                    "1. Utilize LangGraph for deterministic state graph transitions.\n"
                    "2. Enforce Model Context Protocol (MCP) standards for tool discovery.\n"
                    "3. Implement Human-in-the-Loop approval checkpoints before sensitive operations."
                ),
            ),
        ]

        markdown_body = f"# {title}\n\n"
        for s in sections:
            markdown_body += f"## {s.heading}\n\n{s.body}\n\n"

        words = len(markdown_body.split())

        if self.llm:
            prompt = (
                f"Title: {title}\n"
                f"Task: {inp.original_task}\n"
                f"Research: {inp.research_summary}\n"
                f"Insights: {inp.analysis_insights}\n\n"
                "Write a complete, structured executive report in Markdown."
            )
            raw = await self.llm.generate_structured(
                prompt=prompt,
                response_schema=WriterOutput,
                system_prompt=self.system_prompt,
            )
            if "markdown_content" in raw and raw["markdown_content"]:
                return {
                    "title": raw.get("title", title),
                    "summary": raw.get("summary", executive_summary),
                    "markdown_content": raw["markdown_content"],
                    "sections": raw.get("sections", [s.model_dump() for s in sections]),
                    "word_count": raw.get("word_count", len(raw["markdown_content"].split())),
                }

        return {
            "title": title,
            "summary": executive_summary,
            "markdown_content": markdown_body,
            "sections": [s.model_dump() for s in sections],
            "word_count": words,
        }

