from __future__ import annotations

from typing import Any

from app.services.database import Database


class MarksService:
    def __init__(self, database: Database) -> None:
        self.database = database

    def records(
        self,
        student_id: str,
        *,
        subject: str | None = None,
        term: str | None = None,
    ) -> list[dict[str, Any]]:
        filters = ["student_id = ?"]
        params: list[Any] = [student_id]
        if subject:
            filters.append("LOWER(subject) = LOWER(?)")
            params.append(subject)
        if term:
            filters.append("LOWER(term) = LOWER(?)")
            params.append(term)

        query = f"""
            SELECT subject, exam, term, score, max_score
            FROM marks
            WHERE {' AND '.join(filters)}
            ORDER BY subject, exam
        """
        rows = self.database.fetch_all(query, params)
        for row in rows:
            row["percentage"] = round((row["score"] / row["max_score"]) * 100, 2)
        return rows

    def summarize(
        self,
        student_id: str,
        *,
        subject: str | None = None,
        term: str | None = None,
    ) -> dict[str, Any]:
        records = self.records(student_id, subject=subject, term=term)
        if not records:
            return {
                "subject": subject,
                "term": term,
                "records": [],
                "subject_summaries": [],
                "average_percentage": None,
                "highest_subject": None,
                "lowest_subject": None,
                "strong_subjects": [],
                "weak_subjects": [],
            }

        total_score = sum(row["score"] for row in records)
        total_max = sum(row["max_score"] for row in records)
        average = round((total_score / total_max) * 100, 2) if total_max else None
        subject_summaries = _subject_summaries(records)
        ranked_subjects = subject_summaries or records
        highest = max(ranked_subjects, key=lambda row: row["percentage"])
        lowest = min(ranked_subjects, key=lambda row: row["percentage"])
        strong_subjects = [
            row["subject"]
            for row in subject_summaries
            if average is not None and row["percentage"] >= average
        ]
        weak_subjects = [
            row["subject"]
            for row in subject_summaries
            if average is not None and row["percentage"] < average
        ]

        return {
            "subject": subject,
            "term": term,
            "records": records,
            "subject_summaries": subject_summaries,
            "average_percentage": average,
            "highest_subject": highest,
            "lowest_subject": lowest,
            "strong_subjects": strong_subjects,
            "weak_subjects": weak_subjects,
        }


def _subject_summaries(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for row in records:
        subject = row["subject"]
        summary = grouped.setdefault(
            subject,
            {
                "subject": subject,
                "score": 0,
                "max_score": 0,
                "record_count": 0,
                "highest_score": row["score"],
                "lowest_score": row["score"],
            },
        )
        summary["score"] += row["score"]
        summary["max_score"] += row["max_score"]
        summary["record_count"] += 1
        summary["highest_score"] = max(summary["highest_score"], row["score"])
        summary["lowest_score"] = min(summary["lowest_score"], row["score"])

    summaries = []
    for summary in grouped.values():
        max_score = summary["max_score"]
        summary["percentage"] = round((summary["score"] / max_score) * 100, 2) if max_score else None
        summaries.append(summary)
    return sorted(summaries, key=lambda row: row["subject"])
