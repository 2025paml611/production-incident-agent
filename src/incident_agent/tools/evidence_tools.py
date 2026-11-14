"""LangChain tools scoped to one selected synthetic incident scenario."""

import json
from typing import Any

from langchain_core.tools import StructuredTool

from incident_agent.domain.models import IncidentScenario

_MAX_RESULTS = 100


class ScenarioEvidenceTools:
    """Expose fixture evidence through tools bound to one selected scenario."""

    def __init__(self, scenario: IncidentScenario) -> None:
        self._scenario = scenario

    @property
    def scenario_id(self) -> str:
        """ID of the fixture this toolset is permitted to query."""

        return self._scenario.scenario_id

    def as_langchain_tools(self) -> tuple[StructuredTool, ...]:
        """Create LangChain tools whose context is this scenario only."""

        def get_all_metrics() -> str:
            return self.get_metrics()

        def search_all_logs() -> str:
            return self.search_logs()

        def get_all_deployment_history() -> str:
            return self.get_deployment_history()

        return (
            StructuredTool.from_function(
                func=get_all_metrics,
                name="get_metrics",
                description=(
                    "Read metric observations from the currently selected incident "
                    "scenario fixture."
                ),
            ),
            StructuredTool.from_function(
                func=search_all_logs,
                name="search_logs",
                description=(
                    "Read log evidence from the currently selected incident scenario "
                    "fixture."
                ),
            ),
            StructuredTool.from_function(
                func=get_all_deployment_history,
                name="get_deployment_history",
                description=(
                    "Read deployment and configuration events from the currently "
                    "selected incident scenario fixture."
                ),
            ),
            StructuredTool.from_function(
                func=self.check_previous_version,
                name="check_previous_version",
                description=(
                    "Check previous-version health evidence in the currently selected "
                    "incident scenario fixture; report when it was not supplied."
                ),
            ),
        )

    def get_metrics(self, metric_names: list[str] | None = None) -> str:
        """Return source-labelled metric evidence, optionally filtered by name."""

        if metric_names is not None:
            if not isinstance(metric_names, list) or any(
                not isinstance(name, str) or not name.strip()
                for name in metric_names
            ):
                raise ValueError("metric_names must be a list of non-empty strings")

        requested = set(metric_names) if metric_names is not None else None
        matching = [
            {
                "name": metric.name,
                "value": metric.value,
                "unit": metric.unit,
                "source": metric.source,
                "observed_at": metric.observed_at,
                "evidence": f"{metric.name}={metric.value} {metric.unit}",
            }
            for metric in self._scenario.metrics
            if requested is None or metric.name in requested
        ]
        found = {metric["name"] for metric in matching}
        return _json_result(
            {
                "scenario_id": self.scenario_id,
                "time_window": self._scenario.time_window,
                "metrics": matching,
                "not_found": (
                    sorted(requested - found) if requested is not None else []
                ),
            }
        )

    def search_logs(self, query: str = "", limit: int = 20) -> str:
        """Search fixture logs by case-insensitive message, level, or service text."""

        normalized_query = _query_text(query)
        result_limit = _validated_limit(limit)
        terms = normalized_query.casefold().split()
        matching = []
        for entry in self._scenario.logs:
            searchable = " ".join(
                (entry.level, entry.service, entry.message)
            ).casefold()
            if all(term in searchable for term in terms):
                matching.append(
                    {
                        "timestamp": entry.timestamp,
                        "level": entry.level,
                        "service": entry.service,
                        "message": entry.message,
                        "source": entry.source,
                    }
                )
            if len(matching) >= result_limit:
                break

        return _json_result(
            {
                "scenario_id": self.scenario_id,
                "query": normalized_query,
                "logs": matching,
            }
        )

    def get_deployment_history(self, limit: int = 20) -> str:
        """Return recent deployment/configuration evidence for this scenario."""

        result_limit = _validated_limit(limit)
        events = [
            {
                "timestamp": event.timestamp,
                "version": event.version,
                "change_type": event.change_type,
                "summary": event.summary,
                "source": event.source,
            }
            for event in reversed(self._scenario.deployment_history[-result_limit:])
        ]
        return _json_result(
            {
                "scenario_id": self.scenario_id,
                "deployment_history": events,
                "available": bool(events),
                "missing_evidence": (
                    []
                    if events
                    else [
                        "No deployment events were supplied for this scenario fixture."
                    ]
                ),
            }
        )

    def check_previous_version(self) -> str:
        """Return prior-version health or explicitly identify unavailable evidence."""

        previous = self._scenario.previous_version
        if previous is None:
            return _json_result(
                {
                    "scenario_id": self.scenario_id,
                    "available": False,
                    "status": "not_provided",
                    "version": None,
                    "source": "scenario evidence inventory",
                    "limitation": (
                        "Previous-version health was not supplied in this scenario fixture."
                    ),
                }
            )
        return _json_result(
            {
                "scenario_id": self.scenario_id,
                "available": True,
                "status": previous.status.value,
                "version": previous.version,
                "source": previous.source,
            }
        )


def _query_text(query: str) -> str:
    if not isinstance(query, str):
        raise TypeError("query must be a string")
    return query.strip()


def _validated_limit(limit: int) -> int:
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise TypeError("limit must be an integer")
    if not 1 <= limit <= _MAX_RESULTS:
        raise ValueError(f"limit must be between 1 and {_MAX_RESULTS}")
    return limit


def _json_result(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)
