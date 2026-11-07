"""Document Search Tool for knowledge retrieval over local and synthetic corpora."""

import os
from typing import Any, Dict, List
from pydantic import BaseModel, Field
from app.config import settings
from app.tools.base import BaseTool


class DocumentSearchInput(BaseModel):
    query: str = Field(..., min_length=2, description="Search query string or keywords")
    max_results: int = Field(default=3, ge=1, le=10, description="Max documents to return")


DEFAULT_CORPUS = [
    {
        "id": "doc-01",
        "title": "Enterprise AI Trends and Agentic Workflows 2025-2026",
        "content": (
            "Enterprise adoption of generative AI has shifted from simple chat interfaces to autonomous "
            "multi-agent orchestration systems. Platforms leveraging LangGraph enable organizations to construct "
            "deterministic cyclic state machines where agents specialize in planning, research, quantitative analysis, "
            "and quality auditing. Recent industry benchmarks show that multi-agent architectures achieve a 45% reduction "
            "in hallucination rates and a 3.2x speedup in business report generation compared to monolithic single-prompt LLMs. "
            "Crucially, enterprise deployments require strict governance, audit traces, and Human-in-the-Loop approval checkpoints."
        ),
        "source": "Gartner & Enterprise AI Research Consortium",
    },
    {
        "id": "doc-02",
        "title": "Model Context Protocol (MCP) in Production",
        "content": (
            "The Model Context Protocol (MCP) establishes an open standard for LLMs and agent orchestration platforms "
            "to securely discover and invoke tools across distributed servers. MCP decouples tool implementation from "
            "agent runtime, allowing developers to expose calculators, database queries, and vector stores via standardized "
            "JSON-RPC interfaces. Organizations adopting MCP report an 80% decrease in custom integration glue code "
            "and significant security improvements through centralized permission sandboxes."
        ),
        "source": "Open AI Infrastructure Working Group",
    },
    {
        "id": "doc-03",
        "title": "Cloud-Native Multi-Agent System Reliability Patterns",
        "content": (
            "Building resilient multi-agent systems requires treating agent executions as transactional state machines. "
            "Key reliability patterns include state checkpointing, exponential backoff retries for transient model failures, "
            "circuit breakers for external tools, and explicit dependency-aware parallel execution. Asynchronous Python "
            "backends using FastAPI and SQLAlchemy 2.0 with PostgreSQL provide the required scalability and durability."
        ),
        "source": "ACM Distributed Systems Review",
    },
]


class DocumentSearchTool(BaseTool):
    """Tool for querying local document knowledge repositories."""

    id = "document_search"
    name = "Document Search Tool"
    description = (
        "Searches local knowledge repositories and enterprise documents for relevant "
        "passages, metrics, and citations matching query terms."
    )
    parameters_schema = DocumentSearchInput
    is_sensitive = False
    requires_approval = False

    def _load_corpus(self) -> List[Dict[str, str]]:
        docs = list(DEFAULT_CORPUS)
        doc_dir = settings.DOCUMENTS_DIR
        if os.path.exists(doc_dir):
            for filename in os.listdir(doc_dir):
                if filename.endswith((".txt", ".md")):
                    filepath = os.path.join(doc_dir, filename)
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            content = f.read()
                        docs.append({
                            "id": f"file-{filename}",
                            "title": filename.replace("_", " ").replace(".txt", "").title(),
                            "content": content,
                            "source": f"Local Document ({filename})",
                        })
                    except Exception:
                        pass
        return docs

    async def run(self, query: str, max_results: int = 3) -> Dict[str, Any]:
        corpus = self._load_corpus()
        query_tokens = [t.lower() for t in query.split() if len(t) > 2]
        scored_results: List[tuple[float, Dict[str, Any]]] = []

        for doc in corpus:
            text_lower = f"{doc['title']} {doc['content']}".lower()
            score = 0.0
            matched_terms = []
            for token in query_tokens:
                count = text_lower.count(token)
                if count > 0:
                    score += count * 1.5
                    matched_terms.append(token)
                # Boost if in title
                if token in doc["title"].lower():
                    score += 4.0

            if score > 0:
                # Find matching snippet
                snippet = doc["content"][:240] + ("..." if len(doc["content"]) > 240 else "")
                scored_results.append((
                    score,
                    {
                        "document_id": doc["id"],
                        "title": doc["title"],
                        "snippet": snippet,
                        "source": doc["source"],
                        "relevance_score": round(score, 2),
                        "matched_terms": matched_terms,
                    },
                ))

        # Sort descending
        scored_results.sort(key=lambda x: x[0], reverse=True)
        top_matches = [res for _, res in scored_results[:max_results]]

        return {
            "query": query,
            "total_matches": len(top_matches),
            "documents": top_matches,
        }

