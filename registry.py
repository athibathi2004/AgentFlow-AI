"""Central Agent Registry for registration, status tracking, and validation."""

from typing import Any, Dict, List, Optional
from app.agents.analyst import AnalysisAgent
from app.agents.base import BaseAgent
from app.agents.planner import PlannerAgent
from app.agents.researcher import ResearchAgent
from app.agents.reviewer import ReviewerAgent
from app.agents.writer import WriterAgent
from app.core.exceptions import AgentNotFoundError
from app.core.logging import get_logger
from app.llm.base import BaseLLMProvider

logger = get_logger(__name__)


class AgentRegistry:
    """Singleton Registry managing all specialized agents in AgentFlow AI."""

    _instance: Optional["AgentRegistry"] = None

    def __init__(self, default_llm: Optional[BaseLLMProvider] = None) -> None:
        self._agents: Dict[str, BaseAgent] = {}
        self._default_llm = default_llm
        self._register_default_agents()

    @classmethod
    def get_instance(cls, default_llm: Optional[BaseLLMProvider] = None) -> "AgentRegistry":
        if cls._instance is None:
            cls._instance = cls(default_llm=default_llm)
        elif default_llm and cls._instance._default_llm is None:
            cls._instance.set_default_llm(default_llm)
        return cls._instance

    def set_default_llm(self, llm: BaseLLMProvider) -> None:
        """Propagate default LLM provider to all registered agents."""
        self._default_llm = llm
        for agent in self._agents.values():
            if agent.llm is None:
                agent.set_llm_provider(llm)

    def _register_default_agents(self) -> None:
        """Register the 5 core specialized agents."""
        defaults = [
            PlannerAgent(llm_provider=self._default_llm),
            ResearchAgent(llm_provider=self._default_llm),
            AnalysisAgent(llm_provider=self._default_llm),
            WriterAgent(llm_provider=self._default_llm),
            ReviewerAgent(llm_provider=self._default_llm),
        ]
        for agent in defaults:
            self.register(agent)

    def register(self, agent: BaseAgent) -> None:
        """Register an agent in the platform."""
        if self._default_llm and agent.llm is None:
            agent.set_llm_provider(self._default_llm)
        self._agents[agent.id] = agent
        logger.info(f"Registered agent: {agent.id} ({agent.role})")

    def unregister(self, agent_id: str) -> None:
        """Unregister an agent."""
        if agent_id in self._agents:
            del self._agents[agent_id]

    def get(self, agent_id: str) -> BaseAgent:
        """Retrieve agent by ID or raise AgentNotFoundError."""
        agent = self._agents.get(agent_id)
        if not agent:
            # Also try matching by role
            for a in self._agents.values():
                if a.role == agent_id:
                    return a
            raise AgentNotFoundError(f"Agent with identifier '{agent_id}' is not registered")
        return agent

    def exists(self, agent_id: str) -> bool:
        """Check if an agent exists by ID or role."""
        if agent_id in self._agents:
            return True
        return any(a.role == agent_id for a in self._agents.values())

    def enable_agent(self, agent_id: str) -> None:
        """Enable agent."""
        agent = self.get(agent_id)
        agent.is_enabled = True

    def disable_agent(self, agent_id: str) -> None:
        """Disable agent."""
        agent = self.get(agent_id)
        agent.is_enabled = False

    def validate_agent_availability(self, agent_id: str) -> bool:
        """Validate agent exists and is enabled for execution."""
        agent = self.get(agent_id)
        return agent.is_enabled

    def list_agents(self) -> List[Dict[str, Any]]:
        """Return list of metadata for all registered agents."""
        return [agent.get_metadata() for agent in self._agents.values()]

