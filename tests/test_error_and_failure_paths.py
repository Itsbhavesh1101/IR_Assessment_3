from __future__ import annotations

from datetime import date

from app.agents.executor import ToolExecutor
from app.models.schemas import PlanStep
from app.services.students import StudentService
from app.tools.registry import ToolContext, ToolRegistry


def test_invalid_query_returns_structured_error(client):
    response = client.post(
        "/chat",
        json={"student_id": "S001", "message": "Tell me a joke about school."},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["status"] == "error"
    assert payload["error_code"] == "INVALID_QUERY"


def test_missing_records_return_structured_no_records_response(client):
    response = client.post(
        "/chat",
        json={"student_id": "S001", "message": "Show my attendance tomorrow."},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["response"]["status_label"] == "no_records"
    assert payload["response"]["data"]["records"] == []


def test_unknown_tool_is_returned_as_tool_error(database):
    student = StudentService(database).resolve_student("S001")
    registry = ToolRegistry.from_manifest()
    results = ToolExecutor(registry).execute(
        plan=[
            PlanStep(
                step=1,
                intent="unknown",
                tool="missing_tool",
                arguments={},
            )
        ],
        context=ToolContext(
            database=database,
            student=student,
            reference_date=date(2026, 7, 7),
        ),
    )

    assert results[0].status == "error"
    assert results[0].error["error_code"] == "UNKNOWN_TOOL"


def test_executor_continues_after_independent_tool_failure(database):
    student = StudentService(database).resolve_student("S001")
    registry = ToolRegistry.from_manifest()
    results = ToolExecutor(registry).execute(
        plan=[
            PlanStep(
                step=1,
                intent="attendance",
                tool="attendance_tool",
                arguments={"period": "this_month"},
            ),
            PlanStep(
                step=2,
                intent="unknown",
                tool="missing_tool",
                arguments={},
            ),
        ],
        context=ToolContext(
            database=database,
            student=student,
            reference_date=date(2026, 7, 7),
        ),
    )

    assert [result.status for result in results] == ["success", "error"]
    assert results[0].data["attendance_percentage"] == 88.89
    assert results[1].error["error_code"] == "UNKNOWN_TOOL"
