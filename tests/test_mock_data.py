from __future__ import annotations

import json
from pathlib import Path


def test_mock_data_files_are_valid_and_non_empty():
    data_root = Path(__file__).resolve().parents[1] / "mock_data"
    for path in data_root.glob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(payload, list)
        assert payload, f"{path.name} must contain at least one record"


def test_mock_data_has_one_teacher_one_student_and_tool_coverage():
    data_root = Path(__file__).resolve().parents[1] / "mock_data"
    users = json.loads((data_root / "users.json").read_text(encoding="utf-8"))
    students = json.loads((data_root / "students.json").read_text(encoding="utf-8"))
    attendance = json.loads((data_root / "attendance.json").read_text(encoding="utf-8"))
    marks = json.loads((data_root / "marks.json").read_text(encoding="utf-8"))
    fees = json.loads((data_root / "fees.json").read_text(encoding="utf-8"))
    homework = json.loads((data_root / "homework.json").read_text(encoding="utf-8"))
    timetable = json.loads((data_root / "timetable.json").read_text(encoding="utf-8"))

    assert [user["role"] for user in users].count("teacher") == 1
    assert [user["role"] for user in users].count("student") == 1
    assert len(students) == 1
    assert {student["student_id"] for student in students} == {"S001"}
    assert {student_id for user in users for student_id in user["student_ids"]} == {"S001"}

    assert len(attendance) >= 40
    assert any(record["status"] == "absent" for record in attendance)
    assert len(marks) >= 18
    assert {record["subject"] for record in marks}.issuperset({"Mathematics", "Computer Science"})
    assert len(fees) >= 7
    assert any(record["status"] == "unpaid" for record in fees)
    assert len(homework) >= 12
    assert any(task["status"] == "pending" for task in homework)
    assert len(timetable) >= 30
    assert any(entry["subject"] == "Mathematics" for entry in timetable)
