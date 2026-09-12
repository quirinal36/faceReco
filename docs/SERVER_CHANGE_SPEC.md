# edu-manager-api 서버 수정 요청서

> 개인정보 보호를 위해 이름과 학생·수강 식별자, 출석 번호는 가상의 예시 값으로 대체했습니다.

얼굴인식 출석 단말(Jetson / faceReco)을 연동하기 위해 `edu-manager-api` 쪽에 필요한 변경 사항입니다.
2026-09-11 실제 API 응답을 확인한 결과를 근거로 작성했습니다.

---

## 1. 웹훅 시크릿이 서버에 적용돼 있지 않음 (블로커)

### 증상

```
POST https://edu-manager-api.vercel.app/internal/face/check-ins
→ 503 { "error": { "code": "NOT_CONFIGURED",
                   "message": "얼굴인식 등원 웹훅이 설정되지 않았습니다." } }
```

**일부러 틀린 시크릿으로 서명해도 똑같이 503**이 납니다. 서명 검증 이전 단계에서 막히고 있다는 뜻이고,
서버가 `FACE_CHECKIN_WEBHOOK_SECRET` 을 읽지 못하는 상태입니다.

### 확인 사항

1. Vercel 프로젝트 → Settings → Environment Variables 에 `FACE_CHECKIN_WEBHOOK_SECRET` 이 있고
   **Production 스코프가 체크**돼 있는지
2. **환경변수 추가 후 재배포했는지** (Vercel 은 재배포해야 새 환경변수가 적용됩니다)
3. 조직(org)별로 얼굴인식 등원 기능을 켜는 DB 설정이 따로 있다면 그것도 활성화
   (`NOT_CONFIGURED` 는 문서상 "웹훅 시크릿 **또는 조직**이 설정되지 않음" 을 의미)

---

## 2. `attendance_no` 로는 학생을 찾을 수 없음 (블로커)

### 현황 (2026-09-11 실측)

| 항목 | 값 |
|---|---|
| 전체 학생 | 45명 |
| `attendance_no` 보유 | **7명** |
| `legacy_code` 보유 | 35명 |
| **오늘 수업 있는 7명 중 `attendance_no` 보유** | **0명** |

```
이름       attendance_no   legacy_code   status
학생A      None            None          active
학생B      None            90002         active
학생C      None            90003         active
학생D      None            90004         active
학생E      None            None          active
학생F      None            90006         active
학생G      None            90007         active
```

현재 웹훅은 `attendance_no` 로 학생을 찾으므로, 시크릿 문제를 고쳐도 **오늘 명단 전원이
`404 UNKNOWN_STUDENT`** 가 됩니다. `legacy_code` 로 바꿔도 7명 중 2명(학생A·학생E)은 여전히 실패합니다.

### 해결: 웹훅이 `student_id` 도 받도록 확장

`GET /api/v1/attendance/today` 의 `rows[]` 는 이미 `studentId`(UUID)를 내려줍니다.

```json
{
  "enrollmentId": "11111111-1111-4111-8111-111111111111",
  "studentId": "22222222-2222-4222-8222-222222222222",
  "name": "학생A",
  "subject": "인공지능 웹 개발",
  "teacher": "강사A",
  "startTime": "14:00",
  "durationMinutes": 100,
  "checkedInAt": null,
  "source": null
}
```

단말은 이 값을 그대로 되돌려주기만 하면 되므로 **추가 데이터 입력이 전혀 필요 없고,
신규 학생도 자동으로 동작**합니다.

### 요청 스펙

**엔드포인트** `POST /internal/face/check-ins` (변경 없음)

**요청 본문 — `student_id` 필드 추가**

```json
{
  "version": 1,
  "device_id": "jetson-01",
  "student_id": "22222222-2222-4222-8222-222222222222",
  "attendance_no": "90001",
  "checked_in_on": "2026-09-11",
  "checked_in_at": "14:03:21",
  "idempotency_key": "jetson-01:4f7bb96f-…:2026-09-11"
}
```

| 필드 | 변경 | 규칙 |
|---|---|---|
| `student_id` | **신규** | 학생 UUID (`students.id`). 선택 필드 |
| `attendance_no` | 기존 | 선택 필드로 완화 |
| 나머지 | 변경 없음 | |

**필수 조건**: `student_id` 와 `attendance_no` 중 **최소 하나**. 둘 다 없으면 `400 INVALID_PAYLOAD`.

**학생 해석 순서**
1. `student_id` 가 있으면 그것으로 조회 (org 스코프 내)
2. 없으면 기존대로 `attendance_no` 로 조회
3. 둘 다 실패하면 `404 UNKNOWN_STUDENT`

**그 외 동작은 모두 기존 그대로 유지**
- HMAC 서명 검증 (`X-Webhook-Timestamp`, `X-Webhook-Signature`, ±300초)
- `idempotency_key` 재전송 시 `200 duplicate`
- `source` 를 `"face"` 로 기록
- `checked_in_at` 을 출석 시각으로 저장

**응답에 `student_id` 추가 권장** (단말이 응답만으로 대조할 수 있도록)

```json
{ "data": { "check_in_id": "...", "student_id": "...",
            "student_name": "학생A", "outcome": "recorded" } }
```

### 참고: org 스코프

`/internal/*` 은 `X-Organization-Id` 헤더를 쓰지 않으므로, 서버가 `device_id` 또는 시크릿에서
org 를 결정해야 합니다. 현재 단일 org(`00000000-0000-4000-a000-000000000001`) 가정이라면
그대로 두고, 다중 org 를 지원할 계획이라면 `device_id → org_id` 매핑 테이블이 필요합니다.

---

## 3. 수정 후 검증 방법

faceReco 프로젝트에서 아래를 실행하면 **실제 출석 기록을 만들지 않고** 검증됩니다.

```bash
cd backend && ../.venv311/bin/python -m tools.probe_checkin
```

기대 결과:

| 테스트 | 기대 응답 |
|---|---|
| 1. 틀린 시크릿으로 서명 | `401 INVALID_SIGNATURE` |
| 2. 올바른 서명 + 없는 `student_id` | `404 UNKNOWN_STUDENT` |
| 3. 올바른 서명 + 없는 `attendance_no` | `404 UNKNOWN_STUDENT` |

1번이 401, 2·3번이 404 면 서버·서명 모두 정상입니다.
전부 503 이면 1번 항목(시크릿 미적용), 전부 401 이면 시크릿 값 불일치입니다.

실제 학생 한 명으로 최종 확인 (**기록이 생성됩니다**):

```bash
cd backend && ../.venv311/bin/python -m tools.probe_checkin --live --student-id <UUID>
```
