# API Documentation

This project exposes a FastAPI backend with generated Swagger/OpenAPI documentation.

## Open API Docs in the Browser

Start the server:

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Then open:

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- Raw OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`
- Static exported contract: [openapi.json](openapi.json)

If port `8000` is unavailable, run on another port such as `8002` and replace the port in each URL.

## Use Swagger UI

1. Open `http://127.0.0.1:8000/docs`.
2. Expand `POST /auth/login`.
3. Click **Try it out** and submit one of the demo login payloads.
4. Copy the returned `auth_token`.
5. Expand an authenticated endpoint such as `GET /dashboard` or `POST /chat`.
6. Fill the `X-ERP-Auth-Token` header field shown for authenticated endpoints, or add that header when testing through a REST client.
7. Execute the request and inspect the generated response schema, plan, tool output, and error examples.

The Swagger page is generated automatically from the FastAPI route models in `app/models/schemas.py`. The exported `openapi.json` file is the static version of the same contract for submission, Postman import, or external API review.

## Regenerate Static OpenAPI

Run this after changing routes, schemas, or response models:

```powershell
python scripts/export_openapi.py
```

The script writes the current FastAPI OpenAPI schema to `openapi.json`.

## Authentication

The API supports two styles:

1. Login through `POST /auth/login`, then send the returned token in `X-ERP-Auth-Token`.
2. Demo-compatible requests may pass `user_id` directly in query/body parameters.

Token authentication is recommended for the browser UI flow.

Demo credentials:

| Login Type | User ID | Password | Token |
| --- | --- | --- | --- |
| Teacher | `U_TEACHER_10A` | `teacher10a` | `token-teacher-10a` |
| Parent / Student | `U_STUDENT_001` | `student001` | `token-student-001` |

## Endpoint Summary

| Method | Path | Tags | Purpose | Auth |
| --- | --- | --- | --- | --- |
| `POST` | `/auth/login` | auth | Login as teacher or parent/student and receive token | No |
| `GET` | `/health` | system | Basic app/database/provider status | No |
| `GET` | `/readiness` | system | Assignment readiness checklist and data-store evidence | No |
| `GET` | `/tools` | metadata | Tool manifest exposed to clients/evaluators | No |
| `GET` | `/students` | metadata | Active students, optionally scoped to a user/token | Optional |
| `GET` | `/users` | metadata | Active demo users | No |
| `GET` | `/dashboard` | dashboard | Home dashboard metrics, charts, and recent items | Yes |
| `POST` | `/chat` | chat | Natural-language ERP assistant endpoint | Optional/Recommended |
| `GET` | `/chat/history` | chat | Message history for a student/user/conversation | Optional/Recommended |
| `GET` | `/chat/conversations` | chat | Conversation summaries | Optional/Recommended |
| `GET` | `/logs` | logs | Structured audit log entries | Optional/Recommended |

## Core Request and Response Models

### Login Request

```json
{
  "login_type": "teacher",
  "user_id": "U_TEACHER_10A",
  "password": "teacher10a"
}
```

`login_type` accepts:

- `teacher`
- `parent_student`

### Login Response

```json
{
  "auth_token": "token-teacher-10a",
  "user": {
    "user_id": "U_TEACHER_10A",
    "name": "Ms. Nandita Kapoor",
    "role": "teacher"
  },
  "students": [
    {
      "student_id": "S001",
      "name": "Ananya Sharma",
      "role": "student",
      "class_name": "10",
      "section": "A",
      "guardian_name": "Meera Sharma"
    }
  ]
}
```

### Chat Request

```json
{
  "student_id": "S001",
  "conversation_id": null,
  "message": "Show my attendance, Mathematics marks, and pending fees.",
  "return_plan": true
}
```

Optional fields:

- `user_id`: demo user scope when not using token auth.
- `role`: fallback role if no authenticated user is supplied.
- `conversation_id`: reuse this for follow-up questions.
- `return_plan`: set `false` to hide plan steps from the response.

### Chat Response

```json
{
  "conversation_id": "generated-session-id",
  "intent": "attendance+marks+fees",
  "plan": [
    {
      "step": 1,
      "intent": "attendance",
      "tool": "attendance_tool",
      "arguments": {
        "period": "semester",
        "subject": "Mathematics",
        "action": "summary"
      }
    }
  ],
  "tools_used": ["attendance_tool", "marks_tool", "fee_status_tool"],
  "response": {
    "message": "Completed 3 ERP tasks for Ananya Sharma.",
    "status_label": "completed",
    "sections": [],
    "student": {
      "student_id": "S001",
      "name": "Ananya Sharma",
      "class_name": "10",
      "section": "A"
    },
    "llm_generated": true,
    "llm": {
      "provider": "gemini",
      "used": true,
      "status": "generated"
    }
  },
  "status": "success",
  "errors": []
}
```

The `response` object is intentionally flexible because each ERP tool returns a different data shape.

## Example API Calls

### Health

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/health
```

### Login

```powershell
$body = @{
  login_type = "teacher"
  user_id = "U_TEACHER_10A"
  password = "teacher10a"
} | ConvertTo-Json

Invoke-RestMethod `
  -Uri http://127.0.0.1:8000/auth/login `
  -Method Post `
  -ContentType "application/json" `
  -Body $body
```

### Token-Authenticated Chat

```powershell
$body = @{
  student_id = "S001"
  message = "Show my Mathematics marks."
  return_plan = $true
} | ConvertTo-Json

Invoke-RestMethod `
  -Uri http://127.0.0.1:8000/chat `
  -Method Post `
  -ContentType "application/json" `
  -Headers @{ "X-ERP-Auth-Token" = "token-teacher-10a" } `
  -Body $body
```

### Chat History

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/chat/history?student_id=S001&limit=20" `
  -Headers @{ "X-ERP-Auth-Token" = "token-teacher-10a" }
```

### Dashboard

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/dashboard?student_id=S001" `
  -Headers @{ "X-ERP-Auth-Token" = "token-teacher-10a" }
```

## ERP Tool Coverage

The `/chat` endpoint can plan and execute these ERP tools:

| Tool | Supported Questions |
| --- | --- |
| `attendance_tool` | attendance percentage, present classes, missed classes, month/semester filters |
| `marks_tool` | subject marks, averages, highest subject, weak subjects |
| `fee_status_tool` | paid status, pending fees, unpaid records, payment history |
| `homework_tool` | pending homework, today's homework, due tomorrow, subject homework |
| `timetable_tool` | today/tomorrow timetable, first class, subject timing |
| `academic_summary_tool` | combined marks, attendance, homework, and fee summary |
| `recommendation_tool` | focus areas and improvement suggestions |
| `attendance_insight_tool` | target attendance calculations |
| `exam_planner_tool` | multi-day study plan from marks data |
| `parent_report_tool` | parent-facing progress report |

## Error Response Format

Errors use a consistent JSON envelope:

```json
{
  "status": "error",
  "error_code": "INVALID_STUDENT_ID",
  "message": "No active student was found for the provided student_id.",
  "details": {
    "student_id": "missing"
  }
}
```

Common error codes:

| Code | Meaning |
| --- | --- |
| `INVALID_REQUEST` | Request body or query parameters are invalid |
| `EMPTY_REQUEST` | Chat message was blank |
| `INVALID_STUDENT_ID` | Student does not exist or is inactive |
| `INVALID_CREDENTIALS` | Login failed |
| `AUTH_REQUIRED` | Dashboard requires login/token |
| `AUTH_USER_MISMATCH` | Supplied `user_id` does not match token |
| `INVALID_QUERY` | Planner could not identify a supported ERP task |
| `UNKNOWN_TOOL` | Planned tool is not registered |
| `UNEXPECTED_ERROR` | Unhandled server exception |

## Additional API Assets

- [api_examples.http](api_examples.http): REST Client examples.
- [postman_collection.json](postman_collection.json): Postman collection.
- [openapi.json](openapi.json): generated OpenAPI schema.
- Swagger UI: `/docs`.
- ReDoc: `/redoc`.
