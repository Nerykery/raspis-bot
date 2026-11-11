# API Endpoints — ТУСУР Marketplace (Flutter APK)

App type: **Flutter (Dart AOT)** — `lib/arm64-v8a/libapp.so`, Dart **3.0.5**.
Java/DEX layer is only the Flutter embedder + plugins (Sentry, Firebase, AppMetrica) — no app logic.
Endpoints extracted by decompiling the Dart AOT snapshot with **blutter** (`/tmp/blutter_out/asm`).

## Base URLs

| Host | Purpose | Source |
|------|---------|--------|
| `https://api.tusur.ru` | Main REST API (Dio) | `marketplace/config.dart`, `services/dio/dio_module.dart` |
| `https://notifications.tusur.ru` | Push/notifications API | `features/notifications/*` |
| `https://marketplace.tusur.ru` | Web links (not API) | feature pages |
| `https://e586c6f52d07475c880f5d46a5c807fe@sentry.tusur.ru/4` | Sentry DSN | `marketplace/main.dart` |

Auth: `Authorization: Bearer <token>` header injected by Dio (`dio_module.dart`).
Photo URLs: `https://api.tusur.ru/student-photo/` (`config.dart`).

## Tier 1 — Endpoint inventory

### Main API — `https://api.tusur.ru`

| Method | Path | Source (data_source) |
|--------|------|----------------------|
| POST | `/auth/login` | authentication |
| PATCH | `/auth/token` | authentication (refresh) |
| POST | `/api/v1/user/restore-password` | authentication |
| POST | `/api/v1/user/set-password` | user |
| POST | `/api/v1/user/set-email` | user |
| GET | `/api/v1/attendance/by-discipline` | attendance |
| GET | `/api/v1/attendance/miss` | attendance |
| GET | `/api/v1/attendance/by-date` | attendance |
| GET | `/api/v1/company` | companies |
| GET | `/api/v1/company/{id}` | companies |
| GET | `/api/v1/company/filter` | companies |
| POST | `/api/v1/company/{id}/subscriber` | companies (subscribe) |
| DELETE | `/api/v1/company/{id}/subscriber` | companies (unsubscribe) |
| GET | `/api/v1/company/{id}/subscriber/has` | companies (is subscribed) |
| GET | `/api/v1/competence` | competencies (available) |
| GET | `/api/v1/subject-area` | competencies (available) |
| GET | `/api/v1/student/{id}/competence` | competencies (profile) |
| PATCH | `/api/v1/student/{id}/competence` | competencies (update) |
| GET | `/api/v1/student/{id}/subject-area` | competencies (profile) |
| PATCH | `/api/v1/student/{id}/subject-area` | competencies (update) |
| GET | `/api/v1/contact/subdivision` | contacts |
| GET | `/api/v1/contact/subdivision/{id}` | contacts |
| GET | `/api/v1/contact/search` | contacts |
| GET | `/api/v1/edu/program/{id}` | curriculum |
| GET | `/api/v1/edu/discipline/{id}` | curriculum |
| GET | `/api/v1/event` | events |
| GET | `/api/v1/event/{id}` | events |
| GET | `/api/v1/student/{id}/invite` | invitations |
| GET | `/api/v1/invite/{id}` | invitations |
| GET | `/api/v1/invite/filter/student/{id}` | invitations |
| PATCH | `/api/v1/invite/{id}/status` | invitations |
| GET | `/api/v1/media/{id}` | media |
| GET | `/api/v1/news/news` | news |
| GET | `/api/v1/news/news/{id}` | news |
| GET | `/api/v1/contact/person/{id}` | person |
| GET | `/api/v1/timetable/lecture-disciplines/{id}` | person |
| GET | `/api/v1/grade/discipline/{id}` | performance |
| GET | `/api/v1/grade/statistic/{id}` | performance |
| GET | `/api/v1/student/{id}` | profile |
| GET | `/api/v1/student/{id}/portfolio` | profile |
| GET | `/api/v1/student/{id}/review` | profile |
| PATCH | `/api/v1/student/{id}/about` | profile |
| PATCH | `/api/v1/student/{id}/remove-resume` | profile |
| POST | `/api/v1/student/{id}/upload-resume` | profile |
| GET | `/api/v1/notification/config` | profile |
| POST | `/api/v1/notification/config` | profile |
| POST | `/api/v1/notification/fcm/token` | profile |
| GET | `/api/v1/project` | projects |
| GET | `/api/v1/project/{id}` | projects |
| GET | `/api/v1/project/filter` | projects |
| GET | `/api/v1/project/{id}/similar` | projects |
| GET | `/api/v1/project/{id}/bid/has/student/{sid}` | projects (is applied) |
| GET | `/api/v1/student/{id}/project` | projects (user) |
| POST | `/api/v1/bid` | projects (apply) |
| GET | `/api/v1/student/{id}/bid` | applications |
| GET | `/api/v1/bid/{id}` | applications |
| GET | `/api/v1/bid/filter/student/{id}` | applications |
| GET | `/api/v1/student/{id}/report` | reports |
| GET | `/api/v1/student/{id}/report/waiting` | reports |
| POST | `/api/v1/student-report/create` | reports |
| POST | `/api/v1/student-report/{id}/update` | reports |
| GET | `/api/v1/timetable/lessons/{id}` | schedule |
| GET | `/api/v1/timetable/lessons/lecturer` | schedule |
| GET | `/api/v1/timetable/weeks/{id}` | schedule |
| DELETE | `/api/v1/student/{id}/delete` | user (delete profile) |
| PATCH | `/api/v1/student/{id}/feedback` | user (show full review) |

### Notifications API — `https://notifications.tusur.ru`

| Method | Path | Source |
|--------|------|--------|
| POST | `/api/v1/addFcmId` | authentication_repository, settings |
| GET | `/api/v1/getMessages?page=1&perPage=50` | notifications_page |
| GET | `/api/v1/getNewMessagesCount` | main_page, notifications_page |
| GET/POST | `/api/v1/readMarkStatus` | notifications_page |

## Tier 2 — Auth flow

- **Login**: `POST https://api.tusur.ru/auth/login` — body `{ login, password }` → token/session.
- **Refresh**: `PATCH https://api.tusur.ru/auth/token` — refreshes the session token.
- **Bearer injection**: Dio interceptor adds `Authorization: Bearer <token>` to `api.tusur.ru`.
- **FCM**: token registered via `POST https://notifications.tusur.ru/api/v1/addFcmId` (`fcm_id` field).
- **Recovery**: `POST /api/v1/user/restore-password`, then `POST /api/v1/user/set-password`.

## UI routes (not API, for reference)

`/auth`, `/applications/add`, `/reports/add`, `/recover/email`, `/recover/info`,
`/recover/password`, `/recover/password/new`, `/review`, `/showcase-page`, `/subject/:id`.

## Notes / artifacts

- Decompiled Dart sources: `/tmp/blutter_out/asm/marketplace/**`
- Strings dump: `/tmp/libapp_strings.txt`
- APK extracted: `./extracted/`
