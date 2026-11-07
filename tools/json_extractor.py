"""Structured JSON Extraction Tool."""

import json
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.core.exceptions import ToolExecutionError
from app.tools.base import BaseTool


class JsonExtractorInput(BaseModel):
    raw_text: str = Field(..., description="Unstructured text containing embedded JSON or markdown JSON blocks")
    target_keys: Optional[List[str]] = Field(default=None, description="Specific keys to isolate from extracted JSON")


class StructuredJsonExtractorTool(BaseTool):
    """Tool for parsing and extracting structured JSON data from messy LLM or API outputs."""

    id = "json_extractor"
    name = "Structured JSON Extractor Tool"
    description = (
        "Extracts, normalizes, and validates structured JSON blocks embedded within "
        "markdown code fences or conversational text."
    )
    parameters_schema = JsonExtractorInput
    is_sensitive = False
    requires_approval = False

    async def run(
        self,
        raw_text: str,
        target_keys: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        extracted_data = None
        error_notes = []

        # 1. Try markdown code fences ```json ... ```
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw_text)
        candidate_strings = []
        if fence_match:
            candidate_strings.append(fence_match.group(1).strip())

        # 2. Try outermost { ... }
        brace_match = re.search(r"(\{[\s\S]*\})", raw_text)
        if brace_match:
            candidate_strings.append(brace_match.group(1).strip())

        # 3. Try outermost [ ... ]
        bracket_match = re.search(r"(\[[\s\S]*\])", raw_text)
        if bracket_match:
            candidate_strings.append(bracket_match.group(1).strip())

        # 4. Fallback to raw text
        candidate_strings.append(raw_text.strip())

        for candidate in candidate_strings:
            try:
                extracted_data = json.loads(candidate)
                break
            except json.JSONDecodeError as jde:
                error_notes.append(str(jde))
                # Attempt minor syntax repair: remove trailing commas before closing braces
                repaired = re.sub(r",\s*([}\]])", r"\1", candidate)
                try:
                    extracted_data = json.loads(repaired)
                    break
                except Exception:
                    pass

        if extracted_data is None:
            raise ToolExecutionError(
                f"Could not extract valid JSON from input text. Parser errors: {'; '.join(error_notes[:2])}"
            )

        # Filter by target keys if requested
        filtered_view = extracted_data
        if target_keys and isinstance(extracted_data, dict):
            filtered_view = {
                k: extracted_data[k] for k in target_keys if k in extracted_data
            }

        return {
            "extracted_json": filtered_view,
            "data_type": type(extracted_data).__name__,
            "keys_present": list(extracted_data.keys()) if isinstance(extracted_data, dict) else [],
            "item_count": len(extracted_data) if isinstance(extracted_data, (dict, list)) else 1,
        }

