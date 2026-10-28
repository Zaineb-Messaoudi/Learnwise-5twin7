# Learnwise frontend/backend contract

This is the integration agreement for the four Django module owners. The frontend
uses a versioned REST API and one assistant WebSocket. Entity ownership stays
inside the assigned module; foreign keys may reference `accounts.User` and IDs
owned by another module, but modules do not create or mutate each other's entities.

## Shared conventions

- Base URL: `/api/v1`; configure the public origin with `VITE_API_URL`.
- WebSocket base: `VITE_WS_URL`; assistant socket path is listed below.
- Authenticated endpoints use the account session/token established by `accounts`.
- JSON uses UTF-8. Upload endpoints use `multipart/form-data`; the request field
  names below are contractual. Do not manually set multipart `Content-Type`.
- IDs are opaque strings. Timestamps are ISO-8601 UTC. Lists return
  `{ "results": [], "count": 0, "next": null }` (cursor pagination).
- Writes return the created/updated representation and HTTP 201/200. Deletes
  return 204. Validation returns HTTP 400 with
  `{ "detail": "Correct the highlighted fields.", "errors": { "field": ["..."] } }`.
- Processing status values are `queued`, `processing`, `completed`, `failed`.
  Status resources include `progress` (0-100), `updated_at`, and optional
  `error_code`/`error_message`; failed jobs expose an explicit retry endpoint.
- The UI defaults to explicit seeded demo experiences. Set
  `VITE_API_MODE=backend` to use these endpoints and `VITE_API_URL` to point at
  Django. The backend is not implemented yet, so this setting must not be enabled
  against a server without these routes.

## Ownership and frontend surfaces

| Django owner | Owned entities | Frontend surfaces |
|---|---|---|
| `accounts` | `User` | Sign-in, profile, roles, permissions |
| `content_management` | `Course`, `CourseMaterial`, `AudioMaterial`, `DocumentMaterial`, `Transcription`, `Summary` | Teacher courses/materials, upload/processing, transcript/summary review, student course/notebook sources |
| `ai_assistant` | `AssistantSession`, `VoiceQuestion`, `AssistantMessage`, `Explanation`, `Illustration` | Assistant sessions/chat, voice capture and transcript correction, grounded explanation and generated illustration |
| `assessment` | `Quiz`, `Question`, `Choice`, `Exercise`, `QuizAttempt`, `Answer`, `Evaluation` | Teacher generation/review/publish, student quiz/exercise attempt, evaluation and history |
| `learning_analytics` | `LearningPath`, `Enrollment`, `LearningSession`, `LearningActivity`, `Progress`, `Performance`, `Achievement` | Enrollments, dashboard/path, activity, progress/performance, achievements |

The analytics module owns its learning activity/session records and may store
references to a course or assessment ID. It must not create or own those
content/assessment records. Assistant output may cite `CourseMaterial` IDs but
does not mutate course content.
There is no separate `Notebook` entity in the agreed model split. In backend
mode the notebooks navigation groups sources by course and opens the course's
materials; free-form notebook creation remains part of the seeded demo only.

## `accounts`

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/auth/token/` | Login; accepts `{email, password}`, returns `{access, refresh, user}` |
| `POST` | `/auth/token/refresh/` | Refresh access token |
| `POST` | `/auth/logout/` | Revoke current refresh/session |
| `POST` | `/auth/password-reset/` | Request reset email with `{email}`; use a non-enumerating success response |
| `POST` | `/auth/password-reset/confirm/` | Reset with `{token, password}` |
| `POST` | `/accounts/register/` | Create account; accepts `{email, password, first_name, last_name, role}`, returns `{access, refresh, user}` |
| `GET` | `/accounts/me/` | Current `User` and roles |
| `PATCH` | `/accounts/me/` | Update `{first_name, last_name, email}` |

User roles are `student`, `teacher`, and `admin`; authorization is enforced by
the backend for every module endpoint, not by frontend route guards alone.
The user representation includes `{id, email, first_name, last_name, name,
role}`; authentication responses return it alongside the access and refresh
tokens. Refresh may rotate and return a replacement refresh token.

## `content_management`

Course representation: `{id, title, description, level, language, status,
materials_count, created_at, updated_at}`. Material representation includes
`id, course, title, kind (audio|document), file_name, mime_type, size_bytes,
status, progress, created_at`.

| Method | Path | Purpose |
|---|---|---|
| `GET`, `POST` | `/content/courses/` | List/create courses |
| `GET`, `PATCH` | `/content/courses/{course_id}/` | Read/update owned course |
| `POST` | `/content/courses/{course_id}/publish/` | Publish course |
| `GET` | `/content/materials/?course={course_id}` | List materials, optionally by course |
| `POST` | `/content/courses/{course_id}/materials/` | Upload `file` (required), `kind` (required), optional `language` |
| `GET` | `/content/materials/{material_id}/` | Read material |
| `GET` | `/content/materials/{material_id}/processing/` | Read transcription/summary processing status |
| `POST` | `/content/materials/{material_id}/retry/` | Retry a failed processing job |
| `GET`, `PATCH` | `/content/materials/{material_id}/transcription/` | Review/update transcription `text` |
| `GET` | `/content/materials/{material_id}/summary/` | Read `{id, material, text, status, updated_at}` |
| `PATCH` | `/content/materials/{material_id}/summary/` | Save reviewed summary `{text}` |
| `POST` | `/content/materials/{material_id}/summary/regenerate/` | Queue summary regeneration |

Initial upload policy agreed with current UI: PDF/DOCX documents and MP3/WAV
audio up to 250 MiB. Backend may return HTTP 413 with a field-level error if a
deployment configures a lower limit; it must publish the effective limit.

## `ai_assistant`

Message representation: `{id, session, role, content, status, created_at,
explanation?, illustrations: [], citations: []}`. Citations reference content
IDs and include human-readable title/page or timestamp.

| Method | Path | Purpose |
|---|---|---|
| `GET`, `POST` | `/assistant/sessions/` | List/create sessions; create accepts optional `{title, course_id}` |
| `GET`, `PATCH`, `DELETE` | `/assistant/sessions/{session_id}/` | Read/update title/archive session |
| `GET`, `POST` | `/assistant/sessions/{session_id}/messages/` | List/send `{content, course_id?, material_ids?}` |
| `POST` | `/assistant/sessions/{session_id}/voice-questions/` | Upload multipart `audio` (required), optional `language` |
| `GET`, `PATCH` | `/assistant/voice-questions/{question_id}/` | Poll transcription status / correct `{transcript}` |
| `GET` | `/assistant/messages/{message_id}/` | Poll generated explanation/illustrations |

WebSocket: `/ws/assistant/sessions/{session_id}/`. JSON event envelope:
`{type, id, created_at, payload}`. Types: `message.started`,
`message.delta` (`payload.text`), `message.completed` (`payload.message`),
`voice.transcription.completed`, `illustration.completed`, and `error`
(`payload.code`, `payload.message`, `payload.retryable`). REST remains the source
of truth; reconnecting clients can reload messages.

## `assessment`

| Method | Path | Purpose |
|---|---|---|
| `GET`, `POST` | `/assessment/quizzes/` | List/create quiz with course, title, difficulty, questions |
| `GET`, `PATCH`, `DELETE` | `/assessment/quizzes/{quiz_id}/` | Read/edit draft quiz |
| `POST` | `/assessment/generations/` | Generate quiz/exercise draft from `{course_id, material_ids?, source_text?, kind, question_count, difficulty}` |
| `GET` | `/assessment/generations/{generation_id}/` | Poll generation status/results |
| `POST` | `/assessment/quizzes/{quiz_id}/publish/` | Publish reviewed quiz |
| `GET`, `POST` | `/assessment/quizzes/{quiz_id}/attempts/` | List/create attempts; POST returns the user's active attempt if one already exists |
| `PATCH` | `/assessment/quizzes/{quiz_id}/attempts/{attempt_id}/` | Save answer map without submitting |
| `POST` | `/assessment/quizzes/{quiz_id}/attempts/{attempt_id}/submit/` | Submit attempt; returns evaluation |
| `GET` | `/assessment/quizzes/{quiz_id}/attempts/{attempt_id}/evaluation/` | Read score, per-question feedback and suggested next steps |
| `GET`, `POST` | `/assessment/exercises/` | List/create exercises |
| `GET`, `PATCH`, `DELETE` | `/assessment/exercises/{exercise_id}/` | Read/edit draft exercise |
| `POST` | `/assessment/exercises/{exercise_id}/publish/` | Publish reviewed exercise |
| `POST` | `/assessment/exercises/{exercise_id}/submissions/` | Submit answer and receive evaluation/feedback |

Questions own their choices; quiz detail returns `questions: [{id, prompt, type,
choices: [{id, text}]}]`; attempts own an answer map keyed by question ID whose
values are choice IDs. An unanswered question is represented explicitly and
scoring rules are returned by quiz detail. Submission/evaluation responses
include `{score, correct_answers, total_questions, feedback?,
question_feedback: [{question_id, question, is_correct, feedback}]}`; `score`
and `correct_answers` are counts, not percentages.

Exercises expose `{id, title, description, prompt, choices: [{id, text}]}`.
Exercise submission accepts `{answer}` with the selected choice ID and returns
an evaluation with `is_correct` and learner-facing `feedback`.

## `learning_analytics`

| Method | Path | Purpose |
|---|---|---|
| `GET`, `POST` | `/analytics/enrollments/` | List enrollments / enroll with `{course_id}` |
| `GET` | `/analytics/learning-paths/` | List paths for current user |
| `GET` | `/analytics/learning-paths/{path_id}/` | Path nodes, relationships, current/next step |
| `GET`, `POST` | `/analytics/learning-sessions/?from=&to=` | Query sessions by date range; start with `{course_id}` |
| `POST` | `/analytics/learning-sessions/{session_id}/end/` | End a session server-side |
| `GET`, `POST` | `/analytics/learning-activities/?session=` | Read activity timeline or record `{session_id, activity_type, material_id?}`; material IDs are validated against the session course |
| `GET` | `/analytics/progress/?course=` | Progress, completion, topics for optional course |
| `GET` | `/analytics/performance/?range=7d|30d|90d` | Performance trends and topic-level signals |
| `GET` | `/analytics/achievements/` | Earned/in-progress achievements |
| `GET` | `/analytics/student/overview/?range=30d` | Student dashboard aggregate |
| `GET` | `/analytics/teacher/overview/?range=30d` | Teacher aggregate, scoped to authorized courses |
| `GET` | `/analytics/admin/overview/?range=30d` | Admin aggregate |

Analytics responses include a `data_source` (`live` or `demo`) and `range` when
applicable. Empty results are valid and should return empty arrays and zero
counts, not fabricated activity.

`POST /content/materials/{material_id}/complete/` records an idempotent
student completion. Analytics progress and enrollment status are computed
from these server-validated completions; client activity reference IDs cannot
increase progress. Optional processing and summary regeneration endpoints
return `501 Not Implemented` when no processing worker is installed.

`GET /content/courses/?available=true` lists published courses available for
student enrollment; the unfiltered list is scoped to the current teacher's
courses. An enrollment contains `{id, course, progress}` where `course` is the
course representation or its ID, and `progress` is a percentage or progress
object.

`/analytics/student/overview/` returns `stats` (`learning_hours`,
`average_quiz_score`, `streak_days`, `achievement_count`), `weekly_activity`
(`[{label, hours}]`), `focus_areas` (`[{name, score, trend}]`), optional
`next_best_move` (`{course_title, current_topic, next_topic, action,
estimated_minutes, difficulty}`), and optional `path_steps`
(`[{label, title, state}]`). `/analytics/performance/` returns `average_score`,
`strong_topics`, and `topics` (`[{name, score, trend}]`). A learning-path detail
returns `{id, title, description, progress, connected_concepts, nodes:
[{id, title, meta, state, href?}]}`. `/analytics/achievements/` returns
`results: [{id, title, detail, status, progress}]`.

Teacher and admin overviews return `stats` plus `weekly_activity:
[{label, value}]`, optional `recent_activity: [{id, actor_name, action, module,
created_at}]`, `data_source`, and `range`. Teacher stats are `course_count`,
`enrolled_students`, `average_quiz_score`, and `quiz_completion_rate`; admin
stats are `user_count`, `course_count`, `assistant_interactions`, and
`active_users_today`.

## Frontend implementation notes

- Keep each API module under `src/api/` grouped by Django owner; do not put
  assessment writes in content APIs or vice versa.
- Send `FormData` for binary upload and allow the browser to set its multipart
  boundary. Use upload progress events where supported.
- Map processing statuses to readable progress/error/retry UI. Do not present a
  queued upload as completed transcription or generated content.
- In the student notebook workspace, use the course ID as the notebook scope:
  upload/list `CourseMaterial` records, send selected material IDs with every
  assistant message, and render only assistant-returned content and citations.
  Quiz generation uses the assessment generation endpoints. Other text study
  artifacts are assistant responses; audio overview currently means a script,
  since the contract does not include audio synthesis.
- Treat `401` as session expiry; display validation errors beside the field;
  preserve retryable drafts on network errors.
- Face login/attendance is not included in the final four-module model split.
  Do not infer emotion/engagement from face data. Add camera capture only after
  the team defines consent, retention, purpose, and a dedicated backend contract.
