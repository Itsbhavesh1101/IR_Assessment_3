from __future__ import annotations

from time import perf_counter

from app.models.schemas import PlanStep, ToolExecutionResult
from app.tools.registry import ToolContext, ToolRegistry
from app.utils.errors import AppError


class ToolExecutor:
    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    def execute(
        self,
        *,
        plan: list[PlanStep],
        context: ToolContext,
    ) -> list[ToolExecutionResult]:
        results: list[ToolExecutionResult] = []
        for step in plan:
            started = perf_counter()
            try:
                tool = self.registry.get(step.tool)
                data = tool.execute(context, step.arguments)
                results.append(
                    ToolExecutionResult(
                        step=step.step,
                        tool=step.tool,
                        intent=step.intent,
                        status="success",
                        execution_time_ms=round((perf_counter() - started) * 1000, 3),
                        data=data,
                    )
                )
            except AppError as exc:
                results.append(
                    ToolExecutionResult(
                        step=step.step,
                        tool=step.tool,
                        intent=step.intent,
                        status="error",
                        execution_time_ms=round((perf_counter() - started) * 1000, 3),
                        error=exc.to_dict(),
                    )
                )
            except Exception:
                results.append(
                    ToolExecutionResult(
                        step=step.step,
                        tool=step.tool,
                        intent=step.intent,
                        status="error",
                        execution_time_ms=round((perf_counter() - started) * 1000, 3),
                        error={
                            "error_code": "TOOL_FAILURE",
                            "message": "The selected ERP tool failed while processing the request.",
                            "details": {"tool": step.tool},
                        },
                    )
                )
        return results

