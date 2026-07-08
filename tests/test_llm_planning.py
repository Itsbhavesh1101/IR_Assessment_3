from __future__ import annotations

from datetime import date

from app.agents.planner import AgentPlanner
from app.services.students import StudentService
from app.tools.registry import ToolRegistry


class FakeLLMClient:
    def __init__(self, payload=None, exc: Exception | None = None) -> None:
        self.payload = payload or {}
        self.exc = exc

    def generate_json(self, prompt: str):
        if self.exc:
            raise self.exc
        return self.payload


def test_planner_accepts_schema_valid_fake_llm_plan(database):
    student = StudentService(database).resolve_student("S001")
    planner = AgentPlanner(
        database,
        ToolRegistry.from_manifest(),
        FakeLLMClient(
            {
                "steps": [
                    {
                        "step": 1,
                        "intent": "fees",
                        "tool": "fee_status_tool",
                        "arguments": {"only_unpaid": True},
                    }
                ]
            }
        ),
    )

    plan = planner.plan(
        message="Show unpaid fees.",
        student=student,
        recent_context=[],
        reference_date=date(2026, 7, 7),
    )

    assert len(plan) == 1
    assert plan[0].tool == "fee_status_tool"
    assert plan[0].arguments["only_unpaid"] is True


def test_planner_handles_llm_failure_with_fallback(database):
    student = StudentService(database).resolve_student("S001")
    planner = AgentPlanner(
        database,
        ToolRegistry.from_manifest(),
        FakeLLMClient(exc=ValueError("bad llm json")),
    )

    plan = planner.plan(
        message="Show my timetable today.",
        student=student,
        recent_context=[],
        reference_date=date(2026, 7, 7),
    )

    assert [step.tool for step in plan] == ["timetable_tool"]

