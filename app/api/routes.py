from __future__ import annotations

from time import perf_counter

from fastapi import APIRouter, Header, Query

from app.agents.executor import ToolExecutor
from app.agents.llm import build_llm_client
from app.agents.planner import AgentPlanner
from app.agents.responder import ResponseGenerator
from app.memory.store import ConversationMemory
from app.models.schemas import (
    AuthLoginRequest,
    AuthLoginResponse,
    ChatConversationsResponse,
    ChatHistoryResponse,
    ChatRequest,
    ChatResponse,
    DashboardResponse,
    ErrorResponse,
    HealthResponse,
    LogsResponse,
    ReadinessFeature,
    ReadinessResponse,
    StudentsResponse,
    ToolsResponse,
    UsersResponse,
)
from app.services.attendance import AttendanceService
from app.services.audit_logs import AuditLogService
from app.services.database import Database
from app.services.fees import FeeService
from app.services.homework import HomeworkService
from app.services.marks import MarksService
from app.services.students import StudentService
from app.services.timetable import TimetableService
from app.services.users import UserAccessService
from app.tools.registry import ToolContext, ToolRegistry
from app.utils.config import get_settings
from app.utils.dates import today
from app.utils.errors import AppError
from app.utils.logger import JsonAuditLogger
from app.utils.seed_db import ensure_seed_data

router = APIRouter(
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request or query."},
        401: {"model": ErrorResponse, "description": "Invalid ERP auth token."},
        403: {"model": ErrorResponse, "description": "The ERP user cannot access this resource."},
        500: {"model": ErrorResponse, "description": "Unexpected server error."},
    }
)


def _prepared_database() -> Database:
    settings = get_settings()
    database = Database(settings)
    if settings.auto_seed:
        ensure_seed_data(database, settings.mock_data_dir)
    else:
        database.ensure_schema()
    return database


@router.post("/auth/login", response_model=AuthLoginResponse, tags=["auth"])
def login(request: AuthLoginRequest) -> AuthLoginResponse:
    database = _prepared_database()
    access_service = UserAccessService(database)
    user = access_service.authenticate(
        login_type=request.login_type,
        user_id=request.user_id.strip(),
        password=request.password,
    )
    students = access_service.accessible_students(user["user_id"])
    return AuthLoginResponse(
        auth_token=user["api_token"],
        user={
            "user_id": user["user_id"],
            "name": user["name"],
            "role": user["role"],
        },
        students=students,
    )


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    settings = get_settings()
    database = Database(settings)
    database.ensure_schema()
    return HealthResponse(
        status="ok",
        database="ready",
        llm_provider=settings.llm_provider,
        auto_seed=settings.auto_seed,
    )


@router.get("/readiness", response_model=ReadinessResponse, tags=["system"])
def readiness() -> ReadinessResponse:
    database = _prepared_database()
    registry = ToolRegistry.from_manifest()
    manifest = registry.manifest_for_prompt()
    implemented_tools = [tool["name"] for tool in manifest]
    required_tools = [
        "attendance_tool",
        "marks_tool",
        "fee_status_tool",
        "homework_tool",
        "timetable_tool",
    ]
    required_ready = all(tool in implemented_tools for tool in required_tools)
    row_counts = _table_counts(
        database,
        [
            "students",
            "users",
            "attendance",
            "marks",
            "fees",
            "homework",
            "timetable",
            "conversations",
            "chat_messages",
            "execution_logs",
        ],
    )

    return ReadinessResponse(
        status="ready" if required_ready and row_counts["students"] > 0 else "incomplete",
        required_tools=required_tools,
        implemented_tools=implemented_tools,
        bonus_features=[
            _readiness_feature(
                "Multi-step task execution",
                "academic_summary_tool" in implemented_tools,
                "Compound chat requests can plan and execute multiple ERP tools.",
            ),
            _readiness_feature(
                "Academic performance summary",
                "academic_summary_tool" in implemented_tools,
                "academic_summary_tool combines marks, attendance, homework, and fees.",
            ),
            _readiness_feature(
                "Smart recommendations",
                "recommendation_tool" in implemented_tools,
                "recommendation_tool analyzes weak subjects and attendance from ERP data.",
            ),
            _readiness_feature(
                "Attendance insights",
                "attendance_insight_tool" in implemented_tools,
                "attendance_insight_tool calculates target attendance paths.",
            ),
            _readiness_feature(
                "Exam preparation planner",
                "exam_planner_tool" in implemented_tools,
                "exam_planner_tool builds a study plan from marks and days remaining.",
            ),
            _readiness_feature(
                "Parent progress report",
                "parent_report_tool" in implemented_tools,
                "parent_report_tool combines attendance, marks, homework, fees, and suggestions.",
            ),
        ],
        capabilities=[
            _readiness_feature(
                "Agent planning",
                True,
                "POST /chat returns plan steps when return_plan is true.",
            ),
            _readiness_feature(
                "Tool calling",
                required_ready,
                "ToolRegistry loads ERP tools from app/tools/tool_manifest.json.",
            ),
            _readiness_feature(
                "Conversation memory",
                True,
                "ConversationMemory persists exchanges and supports follow-up questions.",
            ),
            _readiness_feature(
                "Structured JSON responses",
                True,
                "FastAPI routes use Pydantic response models.",
            ),
            _readiness_feature(
                "Structured audit logging",
                True,
                "JsonAuditLogger writes JSONL logs and execution_logs rows.",
            ),
            _readiness_feature(
                "Role-aware access",
                row_counts["users"] > 0,
                "UserAccessService scopes students, history, and logs by ERP user.",
            ),
            _readiness_feature(
                "Token-aware access",
                row_counts["users"] > 0,
                "Routes can resolve X-ERP-Auth-Token to an ERP user from mock data.",
            ),
        ],
        data_store={
            "type": "sqlite",
            "tables": row_counts,
        },
        verification={
            "coverage_floor_percent": 90,
            "openapi_export": "openapi.json",
            "api_examples": ["api_examples.http", "postman_collection.json"],
            "offline_demo_provider": "disabled",
        },
    )


@router.get("/tools", response_model=ToolsResponse, tags=["metadata"])
def tools() -> ToolsResponse:
    registry = ToolRegistry.from_manifest()
    return ToolsResponse(tools=registry.manifest_for_prompt())


@router.get("/students", response_model=StudentsResponse, tags=["metadata"])
def students(
    user_id: str | None = Query(default=None),
    auth_token: str | None = Header(default=None, alias="X-ERP-Auth-Token"),
) -> StudentsResponse:
    database = _prepared_database()
    effective_user_id = _effective_user_id(database, user_id=user_id, auth_token=auth_token)
    if effective_user_id:
        return StudentsResponse(students=UserAccessService(database).accessible_students(effective_user_id))
    return StudentsResponse(students=StudentService(database).active_students())


@router.get("/users", response_model=UsersResponse, tags=["metadata"])
def users() -> UsersResponse:
    database = _prepared_database()
    return UsersResponse(users=UserAccessService(database).active_users())


@router.get("/dashboard", response_model=DashboardResponse, tags=["dashboard"])
def dashboard(
    student_id: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    auth_token: str | None = Header(default=None, alias="X-ERP-Auth-Token"),
) -> DashboardResponse:
    settings = get_settings()
    database = _prepared_database()
    effective_user_id = _effective_user_id(database, user_id=user_id, auth_token=auth_token)
    if not effective_user_id:
        raise AppError(
            "AUTH_REQUIRED",
            "Login is required before loading the dashboard.",
            http_status=401,
        )

    access_service = UserAccessService(database)
    user, student = access_service.resolve_accessible_student(
        user_id=effective_user_id,
        student_id=student_id,
    )
    reference_date = today(settings.app_timezone)
    attendance = AttendanceService(database).summarize(
        student["student_id"],
        period="this_month",
        reference_date=reference_date,
    )
    marks = MarksService(database).summarize(student["student_id"])
    fees = FeeService(database).summarize(
        student["student_id"],
        reference_date=reference_date,
    )
    homework = HomeworkService(database).summarize(
        student,
        period="semester",
        reference_date=reference_date,
        status="pending",
    )
    timetable = TimetableService(database).summarize(
        student,
        period="today",
        reference_date=reference_date,
    )

    return DashboardResponse(
        user=user,
        student=student,
        metrics={
            "attendance_percentage": attendance["attendance_percentage"],
            "present_classes": attendance["present_classes"],
            "missed_classes": attendance["missed_classes"],
            "average_marks": marks["average_percentage"],
            "pending_fees": fees["pending_total"],
            "pending_homework": homework["pending_count"],
            "classes_today": timetable["total_classes"],
        },
        charts={
            "attendance_records": attendance["records"],
            "marks_by_subject": [
                {
                    "label": record["subject"],
                    "value": record["percentage"],
                }
                for record in marks["subject_summaries"]
            ],
            "fee_history": fees["history"],
        },
        recent={
            "homework": homework["tasks"][:5],
            "timetable": timetable["entries"],
            "weak_subjects": marks["weak_subjects"],
            "strong_subjects": marks["strong_subjects"],
        },
    )


@router.post("/chat", response_model=ChatResponse, tags=["chat"])
def chat(
    request: ChatRequest,
    auth_token: str | None = Header(default=None, alias="X-ERP-Auth-Token"),
) -> ChatResponse:
    settings = get_settings()
    database = _prepared_database()
    effective_user_id = _effective_user_id(
        database,
        user_id=request.user_id,
        auth_token=auth_token,
    )

    message = request.message.strip()
    if not message:
        raise AppError("EMPTY_REQUEST", "Message cannot be empty.")

    student_service = StudentService(database)
    if effective_user_id:
        user, student = UserAccessService(database).resolve_accessible_student(
            user_id=effective_user_id,
            student_id=request.student_id,
        )
        role = user["role"]
    else:
        student = student_service.resolve_student(request.student_id)
        role = request.role or (student["role"] if student else "student")

    if student is None and request.student_id:
        raise AppError(
            "INVALID_STUDENT_ID",
            "No active student was found for the provided student_id.",
            details={"student_id": request.student_id},
        )
    if student is None:
        raise AppError("NO_STUDENTS", "No active students exist in the mock ERP data.")

    memory = ConversationMemory(database)
    conversation_id = memory.get_or_create(
        conversation_id=request.conversation_id,
        user_id=effective_user_id,
        student_id=student["student_id"],
        role=role,
    )
    recent_context = memory.recent_context(conversation_id)
    reference_date = today(settings.app_timezone)
    registry = ToolRegistry.from_manifest()
    llm_client = build_llm_client(settings)
    planner = AgentPlanner(database, registry, llm_client)
    plan = planner.plan(
        message=message,
        student=student,
        recent_context=recent_context,
        reference_date=reference_date,
    )

    started = perf_counter()
    results = ToolExecutor(registry).execute(
        plan=plan,
        context=ToolContext(
            database=database,
            student=student,
            reference_date=reference_date,
        ),
    )
    execution_time_ms = round((perf_counter() - started) * 1000, 3)
    response_payload = ResponseGenerator(
        llm_client,
        llm_provider=settings.llm_provider,
    ).generate(
        student=student,
        message=message,
        plan=plan,
        results=results,
    )
    errors = [result.error for result in results if result.error]
    if errors and any(result.status == "success" for result in results):
        status = "partial_success"
    elif errors:
        status = "error"
    else:
        status = "success"

    plan_dicts = [step.model_dump() for step in plan]
    result_dicts = [result.model_dump() for result in results]
    tools_used = [step.tool for step in plan]
    intent = "+".join(dict.fromkeys(step.intent for step in plan))

    memory.add_exchange(
        conversation_id=conversation_id,
        user_id=effective_user_id,
        student_id=student["student_id"],
        role=role,
        message=message,
        plan=plan_dicts,
        tool_results=result_dicts,
        response=response_payload,
    )
    JsonAuditLogger(settings, database).log_chat_event(
        conversation_id=conversation_id,
        user_query=message,
        identified_intent=intent,
        selected_tools=tools_used,
        execution_time_ms=execution_time_ms,
        response=response_payload,
        status=status,
    )

    return ChatResponse(
        conversation_id=conversation_id,
        intent=intent,
        plan=plan if request.return_plan else [],
        tools_used=tools_used,
        response=response_payload,
        status=status,
        errors=errors,
    )


@router.get("/chat/conversations", response_model=ChatConversationsResponse, tags=["chat"])
def chat_conversations(
    student_id: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    auth_token: str | None = Header(default=None, alias="X-ERP-Auth-Token"),
) -> ChatConversationsResponse:
    database = _prepared_database()
    effective_user_id = _effective_user_id(database, user_id=user_id, auth_token=auth_token)

    student_ids: list[str] | None = None
    if effective_user_id:
        access_service = UserAccessService(database)
        if student_id:
            access_service.assert_student_access(user_id=effective_user_id, student_id=student_id)
        else:
            student_ids = [
                student["student_id"]
                for student in access_service.accessible_students(effective_user_id)
            ]
    elif student_id:
        student = StudentService(database).resolve_student(student_id)
        if student is None:
            raise AppError(
                "INVALID_STUDENT_ID",
                "No active student was found for the provided student_id.",
                details={"student_id": student_id},
            )

    conversations = ConversationMemory(database).conversations(
        student_id=student_id,
        student_ids=student_ids,
        user_id=effective_user_id,
        limit=limit,
    )
    return ChatConversationsResponse(conversations=conversations)


@router.get("/chat/history", response_model=ChatHistoryResponse, tags=["chat"])
def chat_history(
    student_id: str | None = Query(default=None),
    conversation_id: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    auth_token: str | None = Header(default=None, alias="X-ERP-Auth-Token"),
) -> ChatHistoryResponse:
    database = _prepared_database()
    effective_user_id = _effective_user_id(database, user_id=user_id, auth_token=auth_token)

    student_ids: list[str] | None = None
    if effective_user_id:
        access_service = UserAccessService(database)
        if student_id:
            access_service.assert_student_access(user_id=effective_user_id, student_id=student_id)
        else:
            student_ids = [
                student["student_id"]
                for student in access_service.accessible_students(effective_user_id)
            ]
    elif student_id:
        student = StudentService(database).resolve_student(student_id)
        if student is None:
            raise AppError(
                "INVALID_STUDENT_ID",
                "No active student was found for the provided student_id.",
                details={"student_id": student_id},
            )
    history = ConversationMemory(database).history(
        student_id=student_id,
        student_ids=student_ids,
        user_id=effective_user_id,
        conversation_id=conversation_id,
        limit=limit,
    )
    return ChatHistoryResponse(history=history)


@router.get("/logs", response_model=LogsResponse, tags=["logs"])
def logs(
    student_id: str | None = Query(default=None),
    conversation_id: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    auth_token: str | None = Header(default=None, alias="X-ERP-Auth-Token"),
) -> LogsResponse:
    database = _prepared_database()
    effective_user_id = _effective_user_id(database, user_id=user_id, auth_token=auth_token)

    student_ids: list[str] | None = None
    if effective_user_id:
        access_service = UserAccessService(database)
        if student_id:
            access_service.assert_student_access(user_id=effective_user_id, student_id=student_id)
        else:
            student_ids = [
                student["student_id"]
                for student in access_service.accessible_students(effective_user_id)
            ]
    elif student_id:
        student = StudentService(database).resolve_student(student_id)
        if student is None:
            raise AppError(
                "INVALID_STUDENT_ID",
                "No active student was found for the provided student_id.",
                details={"student_id": student_id},
            )

    return LogsResponse(
        logs=AuditLogService(database).entries(
            conversation_id=conversation_id,
            student_id=student_id,
            student_ids=student_ids,
            user_id=effective_user_id,
            limit=limit,
        )
    )


def _effective_user_id(
    database: Database,
    *,
    user_id: str | None,
    auth_token: str | None,
) -> str | None:
    if not auth_token:
        return user_id

    auth_user = UserAccessService(database).resolve_user_by_token(auth_token)
    auth_user_id = auth_user["user_id"]
    if user_id and user_id != auth_user_id:
        raise AppError(
            "AUTH_USER_MISMATCH",
            "The provided user_id does not match the ERP auth token.",
            http_status=403,
            details={"user_id": user_id},
        )
    return auth_user_id


def _readiness_feature(name: str, ready: bool, evidence: str) -> ReadinessFeature:
    return ReadinessFeature(
        name=name,
        status="ready" if ready else "missing",
        evidence=evidence,
    )


def _table_counts(database: Database, tables: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for table in tables:
        row = database.fetch_one(f"SELECT COUNT(*) AS count FROM {table}")
        counts[table] = int(row["count"]) if row else 0
    return counts
