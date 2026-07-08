from __future__ import annotations

from datetime import date

from app.agents.executor import ToolExecutor
from app.agents.responder import ResponseGenerator
from app.models.schemas import PlanStep
from app.services.attendance import AttendanceService
from app.services.fees import FeeService
from app.services.marks import MarksService
from app.services.students import StudentService
from app.services.timetable import TimetableService
from app.tools.registry import ToolContext, ToolRegistry


def test_seeded_attendance_service_computes_percentage(database):
    summary = AttendanceService(database).summarize(
        "S001",
        period="this_month",
        reference_date=date(2026, 7, 7),
    )

    assert summary["total_classes"] == 36
    assert summary["missed_classes"] == 4
    assert summary["attendance_percentage"] == 88.89


def test_marks_service_finds_highest_and_weak_subjects(database):
    summary = MarksService(database).summarize("S001")

    assert summary["highest_subject"]["subject"] == "Computer Science"
    assert "Hindi" in summary["weak_subjects"]
    assert len(summary["records"]) == 18
    assert len(summary["subject_summaries"]) == 6
    assert [item["subject"] for item in summary["subject_summaries"]].count("Mathematics") == 1


def test_fee_service_reports_pending_amount(database):
    summary = FeeService(database).summarize(
        "S001",
        reference_date=date(2026, 7, 7),
    )

    assert summary["has_pending"] is True
    assert summary["current_month"]["pending_amount"] == 5200


def test_timetable_service_returns_first_class_for_today(database):
    student = StudentService(database).resolve_student("S001")
    summary = TimetableService(database).summarize(
        student,
        period="today",
        reference_date=date(2026, 7, 7),
        first_only=True,
    )

    assert summary["day_of_week"] == "Tuesday"
    assert summary["first_only"] is True
    assert summary["total_classes"] == 1
    assert summary["entries"][0]["period"] == 1
    assert summary["entries"][0]["subject"] == "English"


def test_timetable_service_filters_subject_case_insensitively(database):
    student = StudentService(database).resolve_student("S001")
    summary = TimetableService(database).summarize(
        student,
        period="today",
        reference_date=date(2026, 7, 7),
        subject="mathematics",
    )

    assert summary["day_of_week"] == "Tuesday"
    assert summary["total_classes"] == 1
    assert summary["entries"][0]["subject"] == "Mathematics"
    assert summary["entries"][0]["start_time"] == "09:20"


def test_tool_registry_executes_registered_tool(database):
    student = StudentService(database).resolve_student("S001")
    registry = ToolRegistry.from_manifest()
    plan = [
        PlanStep(
            step=1,
            intent="attendance",
            tool="attendance_tool",
            arguments={"period": "this_month"},
        )
    ]

    results = ToolExecutor(registry).execute(
        plan=plan,
        context=ToolContext(
            database=database,
            student=student,
            reference_date=date(2026, 7, 7),
        ),
    )

    assert results[0].status == "success"
    assert results[0].data["attendance_percentage"] == 88.89


def test_response_generator_can_use_llm_for_natural_message(database):
    class FakeLLMClient:
        def generate_json(self, prompt: str):
            return {
                "message": "LLM-written answer using the ERP facts.",
                "status_label": "reviewed",
                "highlights": ["ERP facts preserved"],
            }

    student = StudentService(database).resolve_student("S001")
    registry = ToolRegistry.from_manifest()
    results = ToolExecutor(registry).execute(
        plan=[
            PlanStep(
                step=1,
                intent="attendance",
                tool="attendance_tool",
                arguments={"period": "this_month"},
            )
        ],
        context=ToolContext(
            database=database,
            student=student,
            reference_date=date(2026, 7, 7),
        ),
    )

    response = ResponseGenerator(FakeLLMClient()).generate(
        student=student,
        message="Show my attendance.",
        plan=[
            PlanStep(
                step=1,
                intent="attendance",
                tool="attendance_tool",
                arguments={"period": "this_month"},
            )
        ],
        results=results,
    )

    assert response["message"] == "LLM-written answer using the ERP facts."
    assert response["status_label"] == "reviewed"
    assert response["llm_generated"] is True
    assert response["data"]["attendance_percentage"] == 88.89
