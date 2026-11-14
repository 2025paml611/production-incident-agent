"""Run all incident agents against one selected scenario."""

from collections.abc import Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Protocol

from incident_agent.agents.classical import (
    GoalBasedAgent,
    LearningAgent,
    ModelBasedReflexAgent,
    SimpleReflexAgent,
    UtilityBasedAgent,
)
from incident_agent.agents.llm import OllamaIncidentAgent
from incident_agent.domain.models import AgentResult, IncidentScenario
from incident_agent.domain.scenarios import ScenarioCatalog, load_scenarios
from incident_agent.storage.experience_store import ExperienceRecord

_REQUIRED_AGENT_IDS = (
    "simple_reflex",
    "model_based_reflex",
    "goal_based",
    "utility_based",
    "learning",
    "llm_ollama",
)


class IncidentAgent(Protocol):
    """Interface implemented by each comparable incident-analysis agent."""

    agent_id: str

    def analyze(self, scenario: IncidentScenario) -> AgentResult: ...


@dataclass(frozen=True, slots=True)
class AgentExecution:
    """One agent's result or an explicit description of its failure."""

    agent_id: str
    result: AgentResult | None
    error: str | None

    def __post_init__(self) -> None:
        if not self.agent_id.strip():
            raise ValueError("agent_id must not be empty")
        if (self.result is None) == (self.error is None):
            raise ValueError("exactly one of result or error must be provided")
        if self.error is not None and not self.error.strip():
            raise ValueError("error must not be empty")

    @property
    def succeeded(self) -> bool:
        """Whether the agent produced a valid result."""

        return self.result is not None


@dataclass(frozen=True, slots=True)
class IncidentRun:
    """Results and failures from comparing every required agent on one scenario."""

    scenario: IncidentScenario
    executions: tuple[AgentExecution, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.executions, tuple):
            raise TypeError("executions must be a tuple")
        execution_ids = tuple(item.agent_id for item in self.executions)
        if execution_ids != _REQUIRED_AGENT_IDS:
            raise ValueError("run must report each required agent exactly once in order")
        for execution in self.executions:
            if execution.result is not None and (
                execution.result.scenario_id != self.scenario.scenario_id
            ):
                raise ValueError("agent result scenario_id must match the selected scenario")

    @property
    def results(self) -> tuple[AgentResult, ...]:
        """Successful results, preserving the required comparison order."""

        return tuple(
            execution.result
            for execution in self.executions
            if execution.result is not None
        )

    @property
    def failures(self) -> tuple[AgentExecution, ...]:
        """Agent executions that failed and include an explicit error."""

        return tuple(execution for execution in self.executions if not execution.succeeded)


class IncidentOrchestrator:
    """Load one scenario and invoke all six agents without hiding failures."""

    def __init__(
        self,
        scenarios: ScenarioCatalog | None = None,
        agents: Sequence[IncidentAgent] | None = None,
    ) -> None:
        self._scenarios = scenarios if scenarios is not None else load_scenarios()
        configured_agents = (
            agents
            if agents is not None
            else (
                SimpleReflexAgent(),
                ModelBasedReflexAgent(),
                GoalBasedAgent(),
                UtilityBasedAgent(),
                LearningAgent(),
                OllamaIncidentAgent(),
            )
        )
        agents_by_id: dict[str, IncidentAgent] = {}
        for agent in configured_agents:
            agent_id = getattr(agent, "agent_id", None)
            analyze = getattr(agent, "analyze", None)
            if not isinstance(agent_id, str) or not agent_id.strip():
                raise TypeError("each agent must define a non-empty string agent_id")
            if not callable(analyze):
                raise TypeError(f"agent {agent_id!r} must provide a callable analyze method")
            if agent_id in agents_by_id:
                raise ValueError(f"duplicate agent_id: {agent_id!r}")
            agents_by_id[agent_id] = agent

        missing_agents = set(_REQUIRED_AGENT_IDS) - agents_by_id.keys()
        unexpected_agents = agents_by_id.keys() - set(_REQUIRED_AGENT_IDS)
        if missing_agents or unexpected_agents:
            raise ValueError(
                f"agent set must contain all six required agents; "
                f"missing={sorted(missing_agents)}, "
                f"unexpected={sorted(unexpected_agents)}"
            )
        self._agents = MappingProxyType(agents_by_id)
        self._learning_agent = agents_by_id["learning"]

    def run(self, scenario_id: str) -> IncidentRun:
        """Run all six agents with the exact same catalog scenario instance."""

        if not isinstance(scenario_id, str) or not scenario_id.strip():
            raise ValueError("scenario_id must be a non-empty string")
        scenario = self._scenarios[scenario_id]
        executions = tuple(
            self._run_agent(agent_id, self._agents[agent_id], scenario)
            for agent_id in _REQUIRED_AGENT_IDS
        )
        return IncidentRun(scenario=scenario, executions=executions)

    def record_learning_outcome(
        self, action_id: str, succeeded: bool
    ) -> ExperienceRecord:
        """Persist learning feedback only when an explicit outcome is supplied."""

        record_outcome = getattr(self._learning_agent, "record_outcome", None)
        if not callable(record_outcome):
            raise TypeError("configured learning agent does not support outcome recording")
        return record_outcome(action_id, succeeded)

    @staticmethod
    def _run_agent(
        agent_id: str, agent: IncidentAgent, scenario: IncidentScenario
    ) -> AgentExecution:
        try:
            result = agent.analyze(scenario)
            if not isinstance(result, AgentResult):
                raise TypeError("analyze must return an AgentResult")
            if result.agent_id != agent_id:
                raise ValueError(
                    f"returned agent_id {result.agent_id!r} does not match "
                    f"registered agent_id {agent_id!r}"
                )
            if result.scenario_id != scenario.scenario_id:
                raise ValueError(
                    f"returned scenario_id {result.scenario_id!r} does not match "
                    f"selected scenario_id {scenario.scenario_id!r}"
                )
        except Exception as error:
            return AgentExecution(
                agent_id=agent_id,
                result=None,
                error=f"{type(error).__name__}: {error}",
            )
        return AgentExecution(agent_id=agent_id, result=result, error=None)
