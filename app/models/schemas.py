from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str
    user_id: str | None = None
    student_id: str | None = None
    role: str | None = None
    conversation_id: str | None = None
    return_plan: bool = True


class PlanStep(BaseModel):
    step: int
    intent: str
    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolExecutionResult(BaseModel):
    step: int
    tool: str
    intent: str
    status: Literal["success", "error"]
    execution_time_ms: float
    data: dict[str, Any] = Field(default_factory=dict)
    error: dict[str, Any] | None = None


class ChatResponse(BaseModel):
    conversation_id: str
    intent: str
    plan: list[PlanStep] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)
    response: dict[str, Any] = Field(default_factory=dict)
    status: Literal["success", "partial_success", "error"]
    errors: list[dict[str, Any]] = Field(default_factory=list)


class ChatHistoryItem(BaseModel):
    conversation_id: str
    user_id: str | None = None
    student_id: str
    role: str
    message: str
    response: dict[str, Any]
    plan: list[dict[str, Any]]
    created_at: str


class ChatHistoryResponse(BaseModel):
    history: list[ChatHistoryItem]


class ChatConversationSummary(BaseModel):
    conversation_id: str
    user_id: str | None = None
    student_id: str
    role: str
    message_count: int
    latest_message: str | None = None
    created_at: str
    updated_at: str


class ChatConversationsResponse(BaseModel):
    conversations: list[ChatConversationSummary]


class HealthResponse(BaseModel):
    status: str
    database: str
    llm_provider: str
    auto_seed: bool


class ReadinessFeature(BaseModel):
    name: str
    status: Literal["ready", "missing"]
    evidence: str


class ReadinessResponse(BaseModel):
    status: Literal["ready", "incomplete"]
    required_tools: list[str]
    implemented_tools: list[str]
    bonus_features: list[ReadinessFeature]
    capabilities: list[ReadinessFeature]
    data_store: dict[str, Any]
    verification: dict[str, Any]


class ToolInfo(BaseModel):
    name: str
    intent: str
    description: str
    examples: list[str]


class ToolsResponse(BaseModel):
    tools: list[ToolInfo]


class StudentInfo(BaseModel):
    student_id: str
    name: str
    role: str
    class_name: str
    section: str
    guardian_name: str | None = None


class StudentsResponse(BaseModel):
    students: list[StudentInfo]


class UserInfo(BaseModel):
    user_id: str
    name: str
    role: str


class UsersResponse(BaseModel):
    users: list[UserInfo]


class AuthLoginRequest(BaseModel):
    login_type: Literal["teacher", "parent_student"]
    user_id: str
    password: str


class AuthLoginResponse(BaseModel):
    auth_token: str
    user: UserInfo
    students: list[StudentInfo]


class DashboardResponse(BaseModel):
    user: UserInfo
    student: StudentInfo
    metrics: dict[str, Any]
    charts: dict[str, Any]
    recent: dict[str, Any]


class AuditLogEntry(BaseModel):
    id: int
    conversation_id: str
    user_id: str | None = None
    student_id: str | None = None
    role: str | None = None
    user_query: str
    identified_intent: str
    selected_tools: list[str]
    execution_time_ms: float
    response: dict[str, Any]
    status: str
    timestamp: str


class LogsResponse(BaseModel):
    logs: list[AuditLogEntry]


class ErrorResponse(BaseModel):
    status: Literal["error"] = "error"
    error_code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
