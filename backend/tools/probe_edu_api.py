"""
edu-manager API 연결 점검 스크립트

실제 응답 형태(특히 attendance/today 의 rows 필드)를 확인하기 위한 개발용 도구입니다.

사용법:
    cd backend && ../.venv311/bin/python -m tools.probe_edu_api
    cd backend && ../.venv311/bin/python -m tools.probe_edu_api --date 2026-09-11
"""

import argparse
import json
import sys

from config import get_settings
from services.edu_api import EduApiClient, EduApiError


def _dump(label: str, value) -> None:
    print(f"\n--- {label} ---")
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def main() -> int:
    parser = argparse.ArgumentParser(description="edu-manager API 연결 점검")
    parser.add_argument('--date', help='조회할 날짜 (YYYY-MM-DD)')
    parser.add_argument('--student', default='', help='학생 검색어')
    args = parser.parse_args()

    settings = get_settings()
    print("=" * 60)
    print("edu-manager API 연결 점검")
    print("=" * 60)
    print(f"base_url        : {settings.api_base_url}")
    print(f"org_id          : {settings.org_id}")
    print(f"read_api_ready  : {settings.read_api_ready}")
    print(f"checkin_ready   : {settings.checkin_ready}")
    if settings.missing_keys():
        print(f"!! 비어 있는 설정 : {settings.missing_keys()}")
        return 1

    client = EduApiClient(settings)

    # 1) 토큰 발급
    try:
        token = client._get_access_token()
        print(f"\n[1/3] 토큰 발급 성공 (길이 {len(token)}자, 앞 12자리 {token[:12]}...)")
    except EduApiError as exc:
        print(f"\n[1/3] 토큰 발급 실패: {exc}")
        return 1

    # 2) 오늘 출석 현황
    try:
        today = client.get_today_attendance(args.date)
        print(f"\n[2/3] attendance/today 조회 성공")
        summary = {k: v for k, v in today.items() if k not in ('rows', 'extras')}
        _dump("요약", summary)
        rows = today.get('rows', [])
        print(f"\nrows 개수: {len(rows)}")
        if rows:
            print(f"rows[0] 필드: {sorted(rows[0].keys())}")
            _dump("rows[0]", rows[0])
        extras = today.get('extras', [])
        print(f"\nextras 개수: {len(extras)}")
        if extras:
            print(f"extras[0] 필드: {sorted(extras[0].keys())}")
            _dump("extras[0]", extras[0])
    except EduApiError as exc:
        print(f"\n[2/3] attendance/today 실패: {exc}")

    # 3) 학생 검색
    try:
        students = client.search_students(args.student, page_size=3)
        print(f"\n[3/3] students 조회 성공 (총 {len(students)}명 반환)")
        if students:
            print(f"student 필드: {sorted(students[0].keys())}")
            _dump("students[0]", students[0])
        else:
            print("검색 결과 없음 — --student 옵션으로 검색어를 지정해 보세요.")
    except EduApiError as exc:
        print(f"\n[3/3] students 실패: {exc}")

    print("\n" + "=" * 60)
    return 0


if __name__ == '__main__':
    sys.exit(main())
