from __future__ import annotations

from datetime import date

from app.agents.llm import DisabledLLMClient
from app.agents.planner import AgentPlanner
from app.services.students import StudentService
from app.tools.registry import ToolRegistry


def test_fallback_planner_selects_multiple_tools(database):
    student = StudentService(database).resolve_student("S001")
    planner = AgentPlanner(database, ToolRegistry.from_manifest(), DisabledLLMClient())

    plan = planner.plan(
        message="Show my attendance, Mathematics marks, and pending fees.",
        student=student,
        recent_context=[],
        reference_date=date(2026, 7, 7),
    )

    assert [step.tool for step in plan] == [
        "attendance_tool",
        "marks_tool",
        "fee_status_tool",
    ]
    assert plan[1].arguments["subject"] == "Mathematics"


def test_fallback_planner_uses_recent_tool_for_follow_up(database):
    student = StudentService(database).resolve_student("S001")
    planner = AgentPlanner(database, ToolRegistry.from_manifest(), DisabledLLMClient())

    plan = planner.plan(
        message="Which one is highest?",
        student=student,
        recent_context=[{"tools_used": ["marks_tool"]}],
        reference_date=date(2026, 7, 7),
    )

    assert [step.tool for step in plan] == ["marks_tool"]
    assert plan[0].arguments["action"] == "highest"


def test_fallback_planner_extracts_attendance_target(database):
    student = StudentService(database).resolve_student("S001")
    planner = AgentPlanner(database, ToolRegistry.from_manifest(), DisabledLLMClient())

    plan = planner.plan(
        message="Can I maintain 90% attendance this semester?",
        student=student,
        recent_context=[],
        reference_date=date(2026, 7, 7),
    )

    assert [step.tool for step in plan] == ["attendance_insight_tool"]
    assert plan[0].arguments["target_percentage"] == 90.0


def test_fallback_planner_extracts_exam_countdown(database):
    student = StudentService(database).resolve_student("S001")
    planner = AgentPlanner(database, ToolRegistry.from_manifest(), DisabledLLMClient())

    plan = planner.plan(
        message="My exams start in 15 days. Create a study plan.",
        student=student,
        recent_context=[],
        reference_date=date(2026, 7, 7),
    )

    assert [step.tool for step in plan] == ["exam_planner_tool"]
    assert plan[0].arguments["days_until_exam"] == 15
