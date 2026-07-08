from __future__ import annotations


def test_academic_performance_summary_uses_multiple_erp_sources(client):
    response = client.post(
        "/chat",
        json={
            "student_id": "S001",
            "message": "Summarize my academic performance this semester.",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    data = payload["response"]["data"]
    assert payload["tools_used"] == ["academic_summary_tool"]
    assert data["marks_summary"]["highest_subject"]["subject"] == "Computer Science"
    assert data["attendance_summary"]["attendance_percentage"] is not None
    assert data["homework_summary"]["pending_count"] >= 0
    assert "fee_summary" in data


def test_smart_recommendations_are_data_driven(client):
    response = client.post(
        "/chat",
        json={"student_id": "S001", "message": "How can I improve my grades?"},
    )

    assert response.status_code == 200
    payload = response.json()
    data = payload["response"]["data"]
    assert payload["tools_used"] == ["recommendation_tool"]
    assert "Hindi" in data["focus_subjects"]
    assert data["suggestions"]
    assert all("reason" in suggestion for suggestion in data["suggestions"])


def test_attendance_insight_calculates_target_path(client):
    response = client.post(
        "/chat",
        json={
            "student_id": "S001",
            "message": "Can I maintain 90% attendance this semester?",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    data = payload["response"]["data"]
    assert payload["tools_used"] == ["attendance_insight_tool"]
    assert data["target_percentage"] == 90.0
    assert data["current_percentage"] == 88.89
    assert data["classes_needed_to_reach_target"] == 4


def test_exam_preparation_planner_uses_marks_to_prioritize_subjects(client):
    response = client.post(
        "/chat",
        json={
            "student_id": "S001",
            "message": "My exams start in 15 days. Create a study plan.",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    data = payload["response"]["data"]
    assert payload["tools_used"] == ["exam_planner_tool"]
    assert data["days_until_exam"] == 15
    assert len(data["study_plan"]) == 15
    assert data["study_plan"][0]["subject"] == "Hindi"
    assert "Hindi" in data["focus_subjects"]


def test_parent_progress_report_combines_required_sections(client):
    response = client.post(
        "/chat",
        json={
            "student_id": "S001",
            "message": "Generate a parent progress report.",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    data = payload["response"]["data"]
    assert payload["tools_used"] == ["parent_report_tool"]
    assert "attendance_summary" in data
    assert "subject_wise_marks" in data
    assert "homework_status" in data
    assert "pending_fees" in data
    assert "suggestions" in data
