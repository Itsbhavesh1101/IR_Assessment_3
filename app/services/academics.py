from __future__ import annotations

from datetime import date
from math import ceil, floor
from typing import Any

from app.services.attendance import AttendanceService
from app.services.database import Database
from app.services.fees import FeeService
from app.services.homework import HomeworkService
from app.services.marks import MarksService


class AcademicInsightService:
    def __init__(self, database: Database) -> None:
        self.attendance = AttendanceService(database)
        self.marks = MarksService(database)
        self.fees = FeeService(database)
        self.homework = HomeworkService(database)

    def performance_summary(
        self,
        student: dict[str, Any],
        *,
        reference_date: date,
    ) -> dict[str, Any]:
        marks = self.marks.summarize(student["student_id"])
        attendance = self.attendance.summarize(
            student["student_id"],
            period="semester",
            reference_date=reference_date,
        )
        homework = self.homework.summarize(
            student,
            period="semester",
            reference_date=reference_date,
            status="pending",
        )
        fees = self.fees.summarize(student["student_id"], reference_date=reference_date)
        average = marks["average_percentage"]
        if average is None:
            overall = "no_records"
        elif average >= 85:
            overall = "strong"
        elif average >= 70:
            overall = "steady"
        else:
            overall = "needs_attention"

        return {
            "overall_performance": overall,
            "marks_summary": marks,
            "attendance_summary": attendance,
            "homework_summary": homework,
            "fee_summary": fees,
        }

    def recommendations(
        self,
        student: dict[str, Any],
        *,
        reference_date: date,
    ) -> dict[str, Any]:
        summary = self.performance_summary(student, reference_date=reference_date)
        suggestions: list[dict[str, Any]] = []
        marks = summary["marks_summary"]
        attendance = summary["attendance_summary"]
        homework = summary["homework_summary"]
        fees = summary["fee_summary"]

        for subject in marks["weak_subjects"]:
            suggestions.append(
                {
                    "area": "marks",
                    "subject": subject,
                    "priority": "high",
                    "reason": "subject_score_below_student_average",
                }
            )

        if attendance["attendance_percentage"] is not None and attendance["attendance_percentage"] < 90:
            suggestions.append(
                {
                    "area": "attendance",
                    "priority": "medium",
                    "reason": "attendance_below_target",
                    "target_percentage": 90,
                }
            )

        if homework["pending_count"] > 0:
            suggestions.append(
                {
                    "area": "homework",
                    "priority": "medium",
                    "reason": "pending_homework_exists",
                    "pending_count": homework["pending_count"],
                }
            )

        if fees["has_pending"]:
            suggestions.append(
                {
                    "area": "fees",
                    "priority": "low",
                    "reason": "fee_balance_pending",
                    "pending_total": fees["pending_total"],
                }
            )

        return {
            "basis": summary,
            "suggestions": suggestions,
            "focus_subjects": marks["weak_subjects"],
        }

    def attendance_insight(
        self,
        student: dict[str, Any],
        *,
        reference_date: date,
        target_percentage: float,
    ) -> dict[str, Any]:
        summary = self.attendance.summarize(
            student["student_id"],
            period="semester",
            reference_date=reference_date,
        )
        current = summary["attendance_percentage"]
        target_ratio = target_percentage / 100
        total = summary["total_classes"]
        present = summary["present_classes"]

        if current is None or total == 0:
            return {
                "target_percentage": target_percentage,
                "current_percentage": current,
                "attendance_summary": summary,
                "is_currently_meeting_target": None,
                "classes_needed_to_reach_target": None,
                "allowable_future_absences": None,
                "status": "no_records",
            }

        is_meeting_target = current >= target_percentage
        classes_needed = None
        allowable_absences = None

        if is_meeting_target:
            if target_ratio > 0:
                allowable_absences = max(floor((present / target_ratio) - total), 0)
        elif target_ratio < 1:
            required = ((target_ratio * total) - present) / (1 - target_ratio)
            classes_needed = max(ceil(required - 1e-9), 0)

        return {
            "target_percentage": target_percentage,
            "current_percentage": current,
            "attendance_summary": summary,
            "is_currently_meeting_target": is_meeting_target,
            "classes_needed_to_reach_target": classes_needed,
            "allowable_future_absences": allowable_absences,
            "status": "meeting_target" if is_meeting_target else "below_target",
        }

    def exam_preparation_plan(
        self,
        student: dict[str, Any],
        *,
        days_until_exam: int,
    ) -> dict[str, Any]:
        marks = self.marks.summarize(student["student_id"])
        records = sorted(
            marks["subject_summaries"],
            key=lambda row: (row["percentage"], row["subject"]),
        )
        if not records or days_until_exam <= 0:
            return {
                "days_until_exam": days_until_exam,
                "marks_summary": marks,
                "study_plan": [],
                "focus_subjects": marks["weak_subjects"],
                "status": "no_plan",
            }

        study_plan = []
        for day_number in range(1, days_until_exam + 1):
            subject_record = records[(day_number - 1) % len(records)]
            study_plan.append(
                {
                    "day": day_number,
                    "subject": subject_record["subject"],
                    "priority": "high"
                    if subject_record["subject"] in marks["weak_subjects"]
                    else "standard",
                    "basis_percentage": subject_record["percentage"],
                }
            )

        return {
            "days_until_exam": days_until_exam,
            "marks_summary": marks,
            "study_plan": study_plan,
            "focus_subjects": marks["weak_subjects"],
            "status": "ready",
        }

    def parent_progress_report(
        self,
        student: dict[str, Any],
        *,
        reference_date: date,
    ) -> dict[str, Any]:
        summary = self.performance_summary(student, reference_date=reference_date)
        recommendations = self.recommendations(student, reference_date=reference_date)
        return {
            "student": {
                "student_id": student["student_id"],
                "name": student["name"],
                "class_name": student["class_name"],
                "section": student["section"],
                "guardian_name": student.get("guardian_name"),
            },
            "attendance_summary": summary["attendance_summary"],
            "subject_wise_marks": summary["marks_summary"]["subject_summaries"],
            "homework_status": summary["homework_summary"],
            "pending_fees": summary["fee_summary"],
            "suggestions": recommendations["suggestions"],
            "overall_performance": summary["overall_performance"],
        }
