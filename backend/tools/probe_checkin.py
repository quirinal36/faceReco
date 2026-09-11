"""
체크인 웹훅 점검 스크립트

서버(`/internal/face/check-ins`) 설정과 HMAC 서명이 올바른지 확인합니다.

기본 모드는 **실제 출석 기록을 만들지 않습니다**.
존재하지 않는 식별자로 요청해서 인증 단계만 통과하는지 검증합니다.

사용법:
    cd backend && ../.venv311/bin/python -m tools.probe_checkin

    # 실제로 한 명을 출석 처리해 최종 확인 (기록이 생깁니다!)
    cd backend && ../.venv311/bin/python -m tools.probe_checkin --live --student-id <UUID>
"""

import argparse
import dataclasses
import json
import sys

from config import get_settings
from services.checkin_client import CheckInClient, CheckInError

FAKE_STUDENT_ID = '00000000-0000-0000-0000-0000000000ff'
FAKE_ATTENDANCE_NO = 'ZZTEST0000'


def _run(label: str, expect: str, fn) -> bool:
    print(f"\n[{label}] 기대: {expect}")
    try:
        result = fn()
        print(f"  응답: outcome={result.outcome} status={result.status_code} "
              f"student={result.student_name} id={result.check_in_id}")
        print(f"  본문: {json.dumps(result.raw, ensure_ascii=False)}")
        return True
    except CheckInError as exc:
        print(f"  거부: status={exc.status_code} code={exc.code}")
        print(f"  메시지: {exc}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="체크인 웹훅 점검")
    parser.add_argument('--live', action='store_true',
                        help='실제 학생을 출석 처리 (기록이 생성됩니다)')
    parser.add_argument('--student-id', help='--live 에서 사용할 학생 UUID')
    parser.add_argument('--attendance-no', help='--live 에서 사용할 출석번호')
    args = parser.parse_args()

    settings = get_settings()
    print("=" * 60)
    print("체크인 웹훅 점검")
    print("=" * 60)
    print(f"endpoint      : {settings.api_base_url}/internal/face/check-ins")
    print(f"device_id     : {settings.device_id}")
    print(f"checkin_ready : {settings.checkin_ready}")
    if not settings.checkin_ready:
        print("!! FACE_CHECKIN_WEBHOOK_SECRET / FACE_DEVICE_ID 를 .env 에 채우세요.")
        return 1

    client = CheckInClient(settings)

    if args.live:
        if not (args.student_id or args.attendance_no):
            print("\n!! --live 에는 --student-id 또는 --attendance-no 가 필요합니다.")
            return 1
        print("\n*** 실제 출석 기록이 생성됩니다 ***")
        ok = _run('LIVE', '201 recorded 또는 200 duplicate',
                  lambda: client.submit(student_id=args.student_id,
                                        attendance_no=args.attendance_no))
        return 0 if ok else 1

    # 1) 시크릿 불일치 → 401 INVALID_SIGNATURE 여야 정상
    wrong = dataclasses.replace(settings, webhook_secret='0' * 64)
    _run('1/3 잘못된 서명', '401 INVALID_SIGNATURE',
         lambda: CheckInClient(wrong).submit(student_id=FAKE_STUDENT_ID))

    # 2) 올바른 서명 + 없는 student_id → 404 UNKNOWN_STUDENT 여야 정상
    _run('2/3 없는 student_id', '404 UNKNOWN_STUDENT',
         lambda: client.submit(student_id=FAKE_STUDENT_ID))

    # 3) 올바른 서명 + 없는 attendance_no → 404 UNKNOWN_STUDENT 여야 정상
    _run('3/3 없는 attendance_no', '404 UNKNOWN_STUDENT',
         lambda: client.submit(attendance_no=FAKE_ATTENDANCE_NO))

    print("\n" + "=" * 60)
    print("판정 기준")
    print("  503 NOT_CONFIGURED  → 서버에 웹훅 시크릿 미설정 (재배포 필요)")
    print("  1번이 401, 2·3번이 404 → 서버·서명 모두 정상. 구현 진행 가능")
    print("  전부 401             → 시크릿 값이 서버와 다름")
    print("  2번만 400/404 code 다름 → student_id 미지원 (서버 수정 필요)")
    print("=" * 60)
    return 0


if __name__ == '__main__':
    sys.exit(main())
