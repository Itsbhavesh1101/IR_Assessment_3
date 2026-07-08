from __future__ import annotations

import json
import re
from datetime import date
from typing import Any

from app.agents.llm import LLMClient
from app.models.schemas import PlanStep
from app.services.database import Database
from app.services.students import StudentService
from app.tools.registry import ToolRegistry
from app.utils.errors import AppError


class AgentPlanner:
    def __init__(
        self,
        database: Database,
        registry: ToolRegistry,
        llm_client: LLMClient,
    ) -> None:
        self.database = database
        self.registry = registry
        self.llm_client = llm_client

    def plan(
        self,
        *,
        message: str,
        student: dict[str, Any],
        recent_context: list[dict[str, Any]],
        reference_date: date,
    ) -> list[PlanStep]:
        cleaned = message.strip()
        if not cleaned:
            raise AppError("EMPTY_REQUEST", "Message cannot be empty.")

        try:
            llm_plan = self._llm_plan(
                message=cleaned,
                student=student,
                recent_context=recent_context,
                reference_date=reference_date,
            )
            if llm_plan:
                return llm_plan
        except Exception:
            pass

        fallback_plan = self._fallback_plan(
            message=cleaned,
            student=student,
            recent_context=recent_context,
        )
        if not fallback_plan:
            raise AppError(
                "INVALID_QUERY",
                "The assistant could not identify an ERP task from the query.",
            )
        return fallback_plan

    def _llm_plan(
        self,
        *,
        message: str,
        student: dict[str, Any],
        recent_context: list[dict[str, Any]],
        reference_date: date,
    ) -> list[PlanStep]:
        subjects = StudentService(self.database).available_subjects(student)
        prompt = (
            "You are an AI planner for a School ERP assistant. "
            "Return only JSON with a 'steps' array. Each step must contain "
            "step, intent, tool, and arguments. Select only tools from the manifest. "
            "Use conversation context for short follow-up questions. "
            f"Current date: {reference_date.isoformat()}.\n"
            f"Available subjects: {json.dumps(subjects)}.\n"
            f"Tool manifest: {json.dumps(self.registry.manifest_for_prompt())}.\n"
            f"Recent conversation: {json.dumps(recent_context[-6:])}.\n"
            f"User message: {message}"
        )
        payload = self.llm_client.generate_json(prompt)
        steps = payload.get("steps", [])
        if not isinstance(steps, list):
            return []

        plan: list[PlanStep] = []
        for index, item in enumerate(steps, start=1):
            if not isinstance(item, dict):
                continue
            tool_name = str(item.get("tool", ""))
            if not self.registry.has(tool_name):
                continue
            tool = self.registry.get(tool_name)
            arguments = item.get("arguments", {})
            if not isinstance(arguments, dict):
                arguments = {}
            plan.append(
                PlanStep(
                    step=int(item.get("step", index)),
                    intent=str(item.get("intent", tool.intent)),
                    tool=tool.name,
                    arguments=arguments,
                )
            )
        return plan

    def _fallback_plan(
        self,
        *,
        message: str,
        student: dict[str, Any],
        recent_context: list[dict[str, Any]],
    ) -> list[PlanStep]:
        lowered = message.lower()
        scored_tools: list[tuple[str, int]] = []
        for tool in self.registry.list_tools():
            score = _score_tool(lowered, tool.name, tool.keywords)
            if score:
                scored_tools.append((tool.name, score))

        if not scored_tools:
            last_tool = self._last_successful_tool(recent_context)
            if last_tool:
                scored_tools.append((last_tool, 1))

        if not scored_tools:
            return []

        ordered_names = [
            tool.name
            for tool in self.registry.list_tools()
            if any(name == tool.name for name, _score in scored_tools)
        ]
        if "parent_report_tool" in ordered_names:
            ordered_names = ["parent_report_tool"]
        elif "exam_planner_tool" in ordered_names:
            ordered_names = ["exam_planner_tool"]
        elif "attendance_insight_tool" in ordered_names:
            ordered_names = ["attendance_insight_tool"]
        elif "academic_summary_tool" in ordered_names:
            ordered_names = ["academic_summary_tool"]
        elif "recommendation_tool" in ordered_names:
            ordered_names = ["recommendation_tool"]

        subjects = StudentService(self.database).available_subjects(student)
        subject = _extract_subject(message, subjects)
        return [
            PlanStep(
                step=index,
                intent=self.registry.get(tool_name).intent,
                tool=tool_name,
                arguments=_arguments_for_tool(tool_name, lowered, subject),
            )
            for index, tool_name in enumerate(ordered_names, start=1)
        ]

    @staticmethod
    def _last_successful_tool(recent_context: list[dict[str, Any]]) -> str | None:
        for item in reversed(recent_context):
            for tool_name in reversed(item.get("tools_used", [])):
                if tool_name:
                    return tool_name
        return None


def _contains_keyword(message: str, keyword: str) -> bool:
    escaped = re.escape(keyword.lower())
    return re.search(rf"\b{escaped}\b", message) is not None


def _score_tool(message: str, tool_name: str, keywords: list[str]) -> int:
    score = sum(1 for keyword in keywords if _contains_keyword(message, keyword))
    if tool_name == "attendance_insight_tool":
        anchors = ["maintain", "target", "reach", "insight"]
        if not _contains_keyword(message, "attendance") or not any(
            _contains_keyword(message, anchor) for anchor in anchors
        ):
            return 0
    if tool_name == "exam_planner_tool":
        anchors = ["exam", "exams", "study"]
        if not any(_contains_keyword(message, anchor) for anchor in anchors):
            return 0
    if tool_name == "parent_report_tool":
        anchors = ["parent", "guardian"]
        if not any(_contains_keyword(message, anchor) for anchor in anchors):
            return 0
    if tool_name == "homework_tool":
        anchors = ["homework", "assignment", "assignments", "due", "submit"]
        if not any(_contains_keyword(message, anchor) for anchor in anchors):
            return 0
    if tool_name == "fee_status_tool":
        anchors = ["fee", "fees", "payment", "paid", "unpaid", "balance"]
        if not any(_contains_keyword(message, anchor) for anchor in anchors):
            return 0
    return score


def _extract_subject(message: str, subjects: list[str]) -> str | None:
    lowered = message.lower()
    for subject in subjects:
        if subject.lower() in lowered:
            return subject
    return None


def _period_from_message(message: str, default: str | None = None) -> str | None:
    if _contains_keyword(message, "tomorrow"):
        return "tomorrow"
    if _contains_keyword(message, "today"):
        return "today"
    if "this month" in message or "current month" in message:
        return "this_month"
    if "last week" in message or "previous week" in message:
        return "last_week"
    if _contains_keyword(message, "semester"):
        return "semester"
    return default


def _percentage_from_message(message: str, default: float) -> float:
    match = re.search(r"\b(\d+(?:\.\d+)?)\s*%", message)
    if match:
        return float(match.group(1))
    return default


def _days_from_message(message: str, default: int) -> int:
    match = re.search(r"\b(\d+)\s+days?\b", message)
    if match:
        return int(match.group(1))
    return default


def _arguments_for_tool(tool_name: str, message: str, subject: str | None) -> dict[str, Any]:
    if tool_name == "attendance_tool":
        action = "summary"
        if _contains_keyword(message, "miss") or _contains_keyword(message, "missed"):
            action = "missed_classes"
        elif _contains_keyword(message, "absent"):
            action = "missed_classes"
        return {
            "period": _period_from_message(message, "semester"),
            "subject": subject,
            "action": action,
        }
    if tool_name == "marks_tool":
        action = "list"
        if _contains_keyword(message, "highest"):
            action = "highest"
        elif _contains_keyword(message, "average"):
            action = "average"
        elif _contains_keyword(message, "weak"):
            action = "weak_subjects"
        return {"subject": subject, "action": action}
    if tool_name == "fee_status_tool":
        action = "history" if _contains_keyword(message, "history") else "status"
        if _contains_keyword(message, "unpaid"):
            action = "unpaid"
        return {
            "month": None,
            "only_unpaid": _contains_keyword(message, "unpaid"),
            "action": action,
        }
    if tool_name == "homework_tool":
        action = "pending" if _contains_keyword(message, "pending") else "list"
        if _contains_keyword(message, "due") or _period_from_message(message) in {"today", "tomorrow"}:
            action = "due"
        return {
            "period": _period_from_message(message),
            "status": "pending" if _contains_keyword(message, "pending") else None,
            "subject": subject,
            "action": action,
        }
    if tool_name == "timetable_tool":
        return {
            "period": _period_from_message(message, "today"),
            "subject": subject,
            "first_only": _contains_keyword(message, "first"),
        }
    if tool_name == "attendance_insight_tool":
        return {
            "target_percentage": _percentage_from_message(message, 90),
        }
    if tool_name == "exam_planner_tool":
        return {
            "days_until_exam": _days_from_message(message, 14),
        }
    if tool_name == "parent_report_tool":
        return {}
    return {}
