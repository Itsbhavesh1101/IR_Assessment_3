from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from app.services.academics import AcademicInsightService
from app.services.attendance import AttendanceService
from app.services.database import Database
from app.services.fees import FeeService
from app.services.homework import HomeworkService
from app.services.marks import MarksService
from app.services.timetable import TimetableService
from app.utils.errors import AppError


@dataclass(frozen=True)
class ToolContext:
    database: Database
    student: dict[str, Any]
    reference_date: date


ToolRunner = Callable[[ToolContext, dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class ERPTool:
    name: str
    intent: str
    description: str
    keywords: list[str]
    examples: list[str]
    runner: ToolRunner

    def execute(self, context: ToolContext, arguments: dict[str, Any]) -> dict[str, Any]:
        return self.runner(context, arguments)


def _attendance_runner(context: ToolContext, arguments: dict[str, Any]) -> dict[str, Any]:
    data = AttendanceService(context.database).summarize(
        context.student["student_id"],
        period=arguments.get("period"),
        reference_date=context.reference_date,
        subject=arguments.get("subject"),
    )
    data["action"] = arguments.get("action", "summary")
    return data


def _marks_runner(context: ToolContext, arguments: dict[str, Any]) -> dict[str, Any]:
    data = MarksService(context.database).summarize(
        context.student["student_id"],
        subject=arguments.get("subject"),
        term=arguments.get("term"),
    )
    data["action"] = arguments.get("action", "list")
    return data


def _fees_runner(context: ToolContext, arguments: dict[str, Any]) -> dict[str, Any]:
    data = FeeService(context.database).summarize(
        context.student["student_id"],
        reference_date=context.reference_date,
        month=arguments.get("month"),
        only_unpaid=bool(arguments.get("only_unpaid", False)),
    )
    data["action"] = arguments.get("action", "status")
    return data


def _homework_runner(context: ToolContext, arguments: dict[str, Any]) -> dict[str, Any]:
    data = HomeworkService(context.database).summarize(
        context.student,
        period=arguments.get("period"),
        reference_date=context.reference_date,
        status=arguments.get("status"),
        subject=arguments.get("subject"),
    )
    data["action"] = arguments.get("action", "list")
    return data


def _timetable_runner(context: ToolContext, arguments: dict[str, Any]) -> dict[str, Any]:
    data = TimetableService(context.database).summarize(
        context.student,
        period=arguments.get("period"),
        reference_date=context.reference_date,
        subject=arguments.get("subject"),
        first_only=bool(arguments.get("first_only", False)),
    )
    data["action"] = "first_class" if arguments.get("first_only") else "list"
    return data


def _academic_summary_runner(context: ToolContext, arguments: dict[str, Any]) -> dict[str, Any]:
    return AcademicInsightService(context.database).performance_summary(
        context.student,
        reference_date=context.reference_date,
    )


def _recommendation_runner(context: ToolContext, arguments: dict[str, Any]) -> dict[str, Any]:
    return AcademicInsightService(context.database).recommendations(
        context.student,
        reference_date=context.reference_date,
    )


def _attendance_insight_runner(context: ToolContext, arguments: dict[str, Any]) -> dict[str, Any]:
    return AcademicInsightService(context.database).attendance_insight(
        context.student,
        reference_date=context.reference_date,
        target_percentage=float(arguments.get("target_percentage", 90)),
    )


def _exam_planner_runner(context: ToolContext, arguments: dict[str, Any]) -> dict[str, Any]:
    return AcademicInsightService(context.database).exam_preparation_plan(
        context.student,
        days_until_exam=int(arguments.get("days_until_exam", 14)),
    )


def _parent_report_runner(context: ToolContext, arguments: dict[str, Any]) -> dict[str, Any]:
    return AcademicInsightService(context.database).parent_progress_report(
        context.student,
        reference_date=context.reference_date,
    )


RUNNERS: dict[str, ToolRunner] = {
    "attendance_tool": _attendance_runner,
    "marks_tool": _marks_runner,
    "fee_status_tool": _fees_runner,
    "homework_tool": _homework_runner,
    "timetable_tool": _timetable_runner,
    "academic_summary_tool": _academic_summary_runner,
    "recommendation_tool": _recommendation_runner,
    "attendance_insight_tool": _attendance_insight_runner,
    "exam_planner_tool": _exam_planner_runner,
    "parent_report_tool": _parent_report_runner,
}


class ToolRegistry:
    def __init__(self, tools: list[ERPTool]) -> None:
        self._tools = {tool.name: tool for tool in tools}

    @classmethod
    def from_manifest(cls, manifest_path: Path | None = None) -> ToolRegistry:
        path = manifest_path or Path(__file__).with_name("tool_manifest.json")
        with path.open("r", encoding="utf-8") as file:
            items = json.load(file)
        tools = []
        for item in items:
            name = item["name"]
            runner = RUNNERS.get(name)
            if runner is None:
                raise AppError(
                    "TOOL_REGISTRY_ERROR",
                    f"No runner registered for tool {name}.",
                    http_status=500,
                )
            tools.append(
                ERPTool(
                    name=name,
                    intent=item["intent"],
                    description=item["description"],
                    keywords=list(item.get("keywords", [])),
                    examples=list(item.get("examples", [])),
                    runner=runner,
                )
            )
        return cls(tools)

    def get(self, name: str) -> ERPTool:
        tool = self._tools.get(name)
        if tool is None:
            raise AppError(
                "UNKNOWN_TOOL",
                "The generated plan selected a tool that is not available.",
                details={"tool": name},
            )
        return tool

    def has(self, name: str) -> bool:
        return name in self._tools

    def list_tools(self) -> list[ERPTool]:
        return list(self._tools.values())

    def manifest_for_prompt(self) -> list[dict[str, Any]]:
        return [
            {
                "name": tool.name,
                "intent": tool.intent,
                "description": tool.description,
                "examples": tool.examples,
            }
            for tool in self.list_tools()
        ]
