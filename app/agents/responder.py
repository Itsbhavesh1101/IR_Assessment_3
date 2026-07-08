from __future__ import annotations

import json
import re
from typing import Any

import httpx

from app.agents.llm import LLMClient
from app.models.schemas import PlanStep, ToolExecutionResult


class ResponseGenerator:
    def __init__(
        self,
        llm_client: LLMClient | None = None,
        *,
        llm_provider: str = "disabled",
    ) -> None:
        self.llm_client = llm_client
        self.llm_provider = llm_provider.strip().lower() or "disabled"

    def generate(
        self,
        *,
        student: dict[str, Any],
        message: str,
        plan: list[PlanStep],
        results: list[ToolExecutionResult],
    ) -> dict[str, Any]:
        successful = [result for result in results if result.status == "success"]
        failed = [result for result in results if result.status == "error"]
        sections = [_section_for_result(result) for result in successful]

        if len(sections) == 1:
            response = sections[0]
        else:
            response = {
                "message": f"Completed {len(sections)} ERP tasks for {student['name']}.",
                "status_label": "partial" if failed else "completed",
                "sections": sections,
            }

        response["student"] = {
            "student_id": student["student_id"],
            "name": student["name"],
            "class_name": student["class_name"],
            "section": student["section"],
        }
        response["query"] = message
        response["plan_summary"] = [
            {"step": step.step, "intent": step.intent, "tool": step.tool}
            for step in plan
        ]
        response["llm_generated"] = False
        response["llm"] = {
            "provider": self.llm_provider,
            "used": False,
            "status": "not_attempted",
        }
        response = self._rewrite_with_llm(
            response=response,
            student=student,
            message=message,
            results=results,
        )
        return response

    def _rewrite_with_llm(
        self,
        *,
        response: dict[str, Any],
        student: dict[str, Any],
        message: str,
        results: list[ToolExecutionResult],
    ) -> dict[str, Any]:
        if self.llm_client is None:
            response["llm"]["status"] = "not_configured"
            return response

        compact_results = [
            {
                "tool": result.tool,
                "intent": result.intent,
                "status": result.status,
                "data": _compact_result_data_for_llm(result.tool, result.data),
                "error": result.error,
            }
            for result in results
        ]
        prompt = (
            "You are an AI School ERP Assistant writing the final answer for a student. "
            "Use only the provided ERP tool results. Do not invent marks, fees, attendance, "
            "homework, timetable entries, dates, names, or IDs. Keep the answer concise and natural. "
            "For marks, use subject_summaries as the subject-level view; do not repeat a subject "
            "only because it has multiple exam records unless the user explicitly asks exam-wise. "
            "Return only JSON with keys: message, status_label, highlights. "
            "highlights must be an array of short strings. If records are missing, say that clearly.\n\n"
            f"Student: {json.dumps(student)}\n"
            f"User question: {message}\n"
            f"Tool results: {json.dumps(compact_results)}\n"
            f"Structured fallback response: {json.dumps(response)}"
        )

        try:
            generated = self.llm_client.generate_json(prompt)
        except Exception as error:
            response["llm"]["status"] = "fallback"
            response["llm"]["error"] = _safe_llm_error(error)
            return response

        llm_message = generated.get("message")
        if isinstance(llm_message, str) and llm_message.strip():
            response["message"] = llm_message.strip()
            response["llm_generated"] = True
            response["llm"]["used"] = True
            response["llm"]["status"] = "generated"

        status_label = generated.get("status_label")
        if isinstance(status_label, str) and status_label.strip():
            response["status_label"] = status_label.strip()

        highlights = generated.get("highlights")
        if isinstance(highlights, list):
            response["highlights"] = [
                item.strip()
                for item in highlights
                if isinstance(item, str) and item.strip()
            ][:6]

        if not response["llm_generated"]:
            response["llm"]["status"] = "fallback"
            response["llm"]["error"] = "LLM returned no usable message."

        return response


def _section_for_result(result: ToolExecutionResult) -> dict[str, Any]:
    if result.tool == "attendance_tool":
        return _attendance_section(result.data)
    if result.tool == "marks_tool":
        return _marks_section(result.data)
    if result.tool == "fee_status_tool":
        return _fees_section(result.data)
    if result.tool == "homework_tool":
        return _homework_section(result.data)
    if result.tool == "timetable_tool":
        return _timetable_section(result.data)
    if result.tool == "academic_summary_tool":
        return _academic_summary_section(result.data)
    if result.tool == "recommendation_tool":
        return _recommendation_section(result.data)
    if result.tool == "attendance_insight_tool":
        return _attendance_insight_section(result.data)
    if result.tool == "exam_planner_tool":
        return _exam_planner_section(result.data)
    if result.tool == "parent_report_tool":
        return _parent_report_section(result.data)
    return {
        "intent": result.intent,
        "message": "The ERP tool returned data successfully.",
        "status_label": "completed",
        "data": result.data,
    }


def _attendance_section(data: dict[str, Any]) -> dict[str, Any]:
    percentage = data.get("attendance_percentage")
    if percentage is None:
        message = "No attendance records matched the requested filters."
    elif data.get("action") == "missed_classes":
        message = f"{data['missed_classes']} missed class(es) matched the requested attendance period."
    else:
        message = (
            f"Attendance is {percentage}% with {data['present_classes']} present "
            f"and {data['missed_classes']} missed classes."
        )
    return {
        "intent": "attendance",
        "message": message,
        "status_label": data.get("standing", "unknown"),
        "data": data,
    }


def _marks_section(data: dict[str, Any]) -> dict[str, Any]:
    summaries = data.get("subject_summaries", [])
    if data.get("average_percentage") is None:
        message = "No marks records matched the requested filters."
    elif data.get("action") == "weak_subjects":
        weak_subjects = data.get("weak_subjects", [])
        if weak_subjects:
            message = "Weak subject focus areas: " + ", ".join(weak_subjects) + "."
        else:
            message = "No weak subjects were found from the available marks records."
    elif data.get("action") == "highest":
        highest = data["highest_subject"]
        message = f"Highest subject is {highest['subject']} with {highest['percentage']}%."
    elif data.get("action") == "average":
        message = f"Average score is {data['average_percentage']}%."
    elif data.get("subject") and summaries:
        subject = summaries[0]["subject"]
        record_count = summaries[0].get("record_count", len(data.get("records", [])))
        message = (
            f"{subject} average is {summaries[0]['percentage']}% across "
            f"{record_count} exam record(s)."
        )
    else:
        highest = data["highest_subject"]["subject"]
        average = data["average_percentage"]
        subject_count = len(summaries)
        message = (
            f"Subject-wise marks are ready for {subject_count} subject(s). "
            f"Average score is {average}%, and the highest subject is {highest}."
        )
    return {
        "intent": "marks",
        "message": message,
        "status_label": "completed",
        "data": data,
    }


def _compact_result_data_for_llm(tool_name: str, data: dict[str, Any]) -> dict[str, Any]:
    if tool_name == "marks_tool":
        return _compact_marks_data(data)
    if tool_name == "academic_summary_tool":
        return {
            **data,
            "marks_summary": _compact_marks_data(data.get("marks_summary", {})),
        }
    if tool_name == "recommendation_tool":
        basis = data.get("basis", {})
        return {
            **data,
            "basis": {
                **basis,
                "marks_summary": _compact_marks_data(basis.get("marks_summary", {})),
            },
        }
    if tool_name == "exam_planner_tool":
        return {
            **data,
            "marks_summary": _compact_marks_data(data.get("marks_summary", {})),
        }
    return data


def _compact_marks_data(data: dict[str, Any]) -> dict[str, Any]:
    compact = {
        "subject": data.get("subject"),
        "term": data.get("term"),
        "action": data.get("action"),
        "average_percentage": data.get("average_percentage"),
        "highest_subject": data.get("highest_subject"),
        "lowest_subject": data.get("lowest_subject"),
        "strong_subjects": data.get("strong_subjects", []),
        "weak_subjects": data.get("weak_subjects", []),
        "subject_summaries": data.get("subject_summaries", []),
    }
    if data.get("subject"):
        compact["exam_records"] = data.get("records", [])
    return compact


def _safe_llm_error(error: Exception) -> str:
    if isinstance(error, httpx.HTTPStatusError):
        message = _http_error_message(error)
        return f"HTTP {error.response.status_code}: {message}"
    message = str(error) or error.__class__.__name__
    message = re.sub(r"([?&]key=)[^&\s]+", r"\1[redacted]", message)
    message = re.sub(r"AIza[0-9A-Za-z_-]+", "[redacted]", message)
    return f"{error.__class__.__name__}: {message[:240]}"


def _http_error_message(error: httpx.HTTPStatusError) -> str:
    try:
        payload = error.response.json()
    except ValueError:
        return error.response.reason_phrase or "LLM provider request failed."

    api_error = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(api_error, dict):
        message = api_error.get("message")
        if isinstance(message, str) and message.strip():
            return message.strip()[:240]
    return error.response.reason_phrase or "LLM provider request failed."


def _fees_section(data: dict[str, Any]) -> dict[str, Any]:
    pending = data.get("pending_total", 0)
    if not data.get("history"):
        message = "No fee records matched the requested filters."
    elif data.get("action") == "unpaid":
        message = f"{len(data['history'])} unpaid fee record(s) matched, with {pending} pending."
    elif data.get("action") == "history":
        message = f"{len(data['history'])} fee payment record(s) matched the request."
    elif pending:
        message = f"Pending fee balance is {pending}."
    else:
        message = "There is no pending fee balance in the matched records."
    return {
        "intent": "fees",
        "message": message,
        "status_label": "pending" if pending else "clear",
        "data": data,
    }


def _homework_section(data: dict[str, Any]) -> dict[str, Any]:
    count = data.get("pending_count", 0)
    if not data.get("tasks"):
        message = "No homework records matched the requested filters."
    elif data.get("action") == "due":
        message = f"{len(data['tasks'])} homework item(s) are due for the requested period."
    elif count:
        message = f"{count} homework item(s) are pending."
    else:
        message = "No homework item is pending in the matched records."
    return {
        "intent": "homework",
        "message": message,
        "status_label": "pending" if count else "clear",
        "data": data,
    }


def _timetable_section(data: dict[str, Any]) -> dict[str, Any]:
    entries = data.get("entries", [])
    if not entries:
        message = "No timetable entries matched the requested filters."
    elif data.get("first_only"):
        first = entries[0]
        message = f"First class is {first['subject']} at {first['start_time']}."
    else:
        noun = "entry" if len(entries) == 1 else "entries"
        message = f"{len(entries)} timetable {noun} matched the request."
    return {
        "intent": "timetable",
        "message": message,
        "status_label": "completed" if entries else "no_records",
        "data": data,
    }


def _academic_summary_section(data: dict[str, Any]) -> dict[str, Any]:
    marks = data["marks_summary"]
    attendance = data["attendance_summary"]
    message = (
        f"Overall performance is {data['overall_performance']} with "
        f"{marks['average_percentage']}% average marks and "
        f"{attendance['attendance_percentage']}% attendance."
    )
    return {
        "intent": "academic_summary",
        "message": message,
        "status_label": data["overall_performance"],
        "data": data,
    }


def _recommendation_section(data: dict[str, Any]) -> dict[str, Any]:
    count = len(data.get("suggestions", []))
    if count:
        message = f"{count} recommendation(s) were generated from ERP records."
    else:
        message = "No improvement recommendation was needed from the current records."
    return {
        "intent": "recommendations",
        "message": message,
        "status_label": "actionable" if count else "clear",
        "data": data,
    }


def _attendance_insight_section(data: dict[str, Any]) -> dict[str, Any]:
    if data["status"] == "no_records":
        message = "No attendance records are available for this attendance insight."
    elif data["is_currently_meeting_target"]:
        message = (
            f"Current attendance is {data['current_percentage']}%, which meets the "
            f"{data['target_percentage']}% target."
        )
    else:
        message = (
            f"Current attendance is {data['current_percentage']}%, below the "
            f"{data['target_percentage']}% target."
        )
    return {
        "intent": "attendance_insights",
        "message": message,
        "status_label": data["status"],
        "data": data,
    }


def _exam_planner_section(data: dict[str, Any]) -> dict[str, Any]:
    plan_length = len(data.get("study_plan", []))
    if plan_length:
        message = f"Created a {plan_length}-day exam preparation plan."
    else:
        message = "No exam preparation plan could be created from the available marks records."
    return {
        "intent": "exam_planner",
        "message": message,
        "status_label": data["status"],
        "data": data,
    }


def _parent_report_section(data: dict[str, Any]) -> dict[str, Any]:
    message = (
        f"Parent progress report is ready with overall performance marked as "
        f"{data['overall_performance']}."
    )
    return {
        "intent": "parent_progress_report",
        "message": message,
        "status_label": data["overall_performance"],
        "data": data,
    }
