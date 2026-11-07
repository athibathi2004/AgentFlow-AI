"""Text Summarization Tool."""

import re
from typing import Any, Dict, List
from pydantic import BaseModel, Field
from app.core.exceptions import ToolExecutionError
from app.tools.base import BaseTool


class SummarizerInput(BaseModel):
    text: str = Field(..., min_length=20, description="Source text to summarize")
    max_bullets: int = Field(default=3, ge=1, le=10, description="Maximum bullet points to generate")
    focus_topic: str | None = Field(default=None, description="Optional topic to focus summary upon")


class TextSummarizationTool(BaseTool):
    """Tool for structured text summarization and key insight extraction."""

    id = "summarizer"
    name = "Text Summarization Tool"
    description = (
        "Extracts core insights, concise executive summaries, and key takeaways "
        "from technical documents and unstructured prose."
    )
    parameters_schema = SummarizerInput
    is_sensitive = False
    requires_approval = False

    async def run(
        self,
        text: str,
        max_bullets: int = 3,
        focus_topic: str | None = None,
    ) -> Dict[str, Any]:
        cleaned = text.strip()
        words = cleaned.split()
        total_words = len(words)

        # Split sentences cleanly
        sentences = [
            s.strip()
            for s in re.split(r"(?<=[.!?])\s+", cleaned)
            if len(s.strip()) > 15
        ]

        if not sentences:
            raise ToolExecutionError("Input text contains insufficient distinct sentences for summarization")

        # Rank sentences based on word frequency or focus topic
        scored_sentences: List[tuple[float, str]] = []
        topic_words = set(focus_topic.lower().split()) if focus_topic else set()

        for idx, sentence in enumerate(sentences):
            score = 1.0 / (idx + 1)  # Positional weight favoring beginning
            s_lower = sentence.lower()
            if topic_words:
                matches = sum(1 for tw in topic_words if tw in s_lower)
                score += matches * 2.5
            # Favor sentences with technical indicators or numbers
            if any(char.isdigit() for char in sentence):
                score += 0.8
            scored_sentences.append((score, sentence))

        # Sort descending by score
        scored_sentences.sort(key=lambda x: x[0], reverse=True)
        top_sentences = [s for _, s in scored_sentences[:max_bullets]]

        executive_summary = " ".join(top_sentences[:2])
        key_takeaways = [f"• {s}" for s in top_sentences]

        summary_words = len(executive_summary.split())
        reduction_pct = round(
            (1.0 - (summary_words / max(total_words, 1))) * 100, 1
        ) if total_words > 0 else 0.0

        return {
            "executive_summary": executive_summary,
            "key_takeaways": key_takeaways,
            "metrics": {
                "original_word_count": total_words,
                "summary_word_count": summary_words,
                "reduction_percentage": max(0.0, reduction_pct),
                "sentence_count": len(sentences),
            },
        }

