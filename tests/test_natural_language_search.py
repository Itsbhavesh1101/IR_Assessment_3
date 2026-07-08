from __future__ import annotations

import json
from pathlib import Path

from app.utils.config import get_settings
from app.utils.dates import day_name_for_period, period_bounds, today

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_weak_subject_search_returns_action_specific_response(client):
    response = client.post(
        "/chat",
        json={"student_id": "S001", "message": "Which subjects am I weak in?"},
    )

    assert response.status_code == 200
    payload = response.json()
    data = payload["response"]["data"]
    assert payload["tools_used"] == ["marks_tool"]
    assert data["action"] == "weak_subjects"
    assert "Hindi" in data["weak_subjects"]
    assert "Weak subject focus areas" in payload["response"]["message"]


def test_missed_classes_last_week_search_returns_missed_count(client):
    response = client.post(
        "/chat",
        json={"student_id": "S001", "message": "Did I miss any classes last week?"},
    )

    assert response.status_code == 200
    payload = response.json()
    data = payload["response"]["data"]
    assert payload["tools_used"] == ["attendance_tool"]
    assert data["action"] == "missed_classes"
    assert data["period"] == "last_week"
    assert data["missed_classes"] == 3
    assert "missed class" in payload["response"]["message"]


def test_unpaid_fee_search_filters_to_unpaid_records(client):
    response = client.post(
        "/chat",
        json={"student_id": "S001", "message": "Show only unpaid fees."},
    )

    assert response.status_code == 200
    payload = response.json()
    data = payload["response"]["data"]
    assert payload["tools_used"] == ["fee_status_tool"]
    assert data["action"] == "unpaid"
    assert len(data["history"]) == 1
    assert data["history"][0]["status"] == "unpaid"
    assert data["pending_total"] == 5200


def test_due_homework_search_uses_due_period(client):
    response = client.post(
        "/chat",
        json={"student_id": "S001", "message": "What homework is due tomorrow?"},
    )

    assert response.status_code == 200
    payload = response.json()
    data = payload["response"]["data"]
    assert payload["tools_used"] == ["homework_tool"]
    assert data["action"] == "due"
    assert data["period"] == "tomorrow"
    assert len(data["tasks"]) == 1
    assert data["tasks"][0]["subject"] == _expected_homework_subject_for_tomorrow()


def test_first_class_search_uses_timetable_context(client):
    response = client.post(
        "/chat",
        json={"student_id": "S001", "message": "What is my first class today?"},
    )

    assert response.status_code == 200
    payload = response.json()
    data = payload["response"]["data"]
    assert payload["tools_used"] == ["timetable_tool"]
    assert data["action"] == "first_class"
    assert data["first_only"] is True
    expected = _expected_timetable_entries("today")
    assert data["day_of_week"] == day_name_for_period("today", _reference_date())
    assert data["entries"][0]["subject"] == expected[0]["subject"]
    assert f"First class is {expected[0]['subject']}" in payload["response"]["message"]


def test_tomorrow_timetable_search_returns_next_day_schedule(client):
    response = client.post(
        "/chat",
        json={"student_id": "S001", "message": "Show tomorrow's timetable."},
    )

    assert response.status_code == 200
    payload = response.json()
    data = payload["response"]["data"]
    assert payload["tools_used"] == ["timetable_tool"]
    assert data["period"] == "tomorrow"
    assert data["day_of_week"] == day_name_for_period("tomorrow", _reference_date())
    assert [entry["subject"] for entry in data["entries"]] == [
        entry["subject"] for entry in _expected_timetable_entries("tomorrow")
    ]


def _reference_date():
    return today(get_settings().app_timezone)


def _load_mock_data(filename: str):
    return json.loads((PROJECT_ROOT / "mock_data" / filename).read_text(encoding="utf-8"))


def _expected_homework_subject_for_tomorrow() -> str:
    start, _end = period_bounds("tomorrow", _reference_date())
    tasks = [
        item
        for item in _load_mock_data("homework.json")
        if item["class_name"] == "10"
        and item["section"] == "A"
        and item["due_date"] == start.isoformat()
    ]
    tasks.sort(key=lambda item: (item["due_date"], item["subject"]))
    return tasks[0]["subject"]


def _expected_timetable_entries(period: str):
    day_name = day_name_for_period(period, _reference_date())
    entries = [
        item
        for item in _load_mock_data("timetable.json")
        if item["class_name"] == "10"
        and item["section"] == "A"
        and item["day_of_week"] == day_name
    ]
    return sorted(entries, key=lambda item: item["period"])
