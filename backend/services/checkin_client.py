"""
edu-manager 출석 체크인 전송 클라이언트

`/internal/face/check-ins` 웹훅 엔드포인트로 출석을 전송합니다.
Bearer 토큰이 아니라 HMAC-SHA256 서명으로 인증합니다.

서명 규칙:
    X-Webhook-Timestamp : 현재 Unix epoch 초 (10자리 문자열)
    X-Webhook-Signature : "sha256=" + hex(HMAC_SHA256(secret, f"{timestamp}." + rawBody))

주의: 서명 대상은 **실제로 전송되는 바이트 그대로의 본문**입니다.
      서명 후 재직렬화하면 서명이 깨지므로 bytes 를 그대로 전송합니다.
"""

import hashlib
import hmac
import json
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

import requests

from config import Settings, get_settings

CHECKIN_PATH = '/internal/face/check-ins'
PAYLOAD_VERSION = 1


class CheckInError(Exception):
    """체크인 전송 실패"""

    def __init__(self, message: str, status_code: Optional[int] = None,
                 code: Optional[str] = None, retryable: bool = False):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.retryable = retryable


@dataclass
class CheckInResult:
    """체크인 전송 결과"""
    outcome: str                      # recorded / duplicate
    status_code: int
    check_in_id: Optional[str] = None
    student_name: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None

    @property
    def succeeded(self) -> bool:
        """새로 기록됐거나 이미 기록돼 있으면 성공으로 간주"""
        return self.outcome in ('recorded', 'duplicate')


def sign_payload(secret: str, timestamp: str, raw_body: bytes) -> str:
    """HMAC-SHA256 서명 문자열 생성"""
    message = timestamp.encode('utf-8') + b'.' + raw_body
    digest = hmac.new(secret.encode('utf-8'), message, hashlib.sha256).hexdigest()
    return f'sha256={digest}'


def build_idempotency_key(device_id: str, identifier: str, checked_in_on: str) -> str:
    """단말 + 학생 + 날짜 조합의 멱등키 (재전송 시 중복 기록 방지)"""
    return f'{device_id}:{identifier}:{checked_in_on}'


class CheckInClient:
    """얼굴인식 출석 체크인 전송 (스레드 안전)"""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self._session = requests.Session()
        self._lock = threading.Lock()

    def submit(
        self,
        attendance_no: Optional[str] = None,
        student_id: Optional[str] = None,
        checked_in_on: Optional[str] = None,
        checked_in_at: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> CheckInResult:
        """
        출석 체크인 전송

        학생 식별은 student_id(UUID) 를 우선 사용하고, 없으면 attendance_no 를 보냅니다.
        오늘 명단(attendance/today)의 rows[] 가 studentId 를 내려주므로 통상 student_id 로 전송합니다.

        Args:
            attendance_no: 학생 출석번호 (student_id 가 없을 때 사용)
            student_id: 학생 UUID
            checked_in_on: 출석 날짜 YYYY-MM-DD (생략 시 단말 로컬 기준 오늘)
            checked_in_at: 출석 시각 HH:MM:SS (생략 시 단말 로컬 현재 시각)
            idempotency_key: 멱등키 (생략 시 자동 생성)

        Returns:
            CheckInResult

        Raises:
            CheckInError: 설정 누락, 식별자 누락, 네트워크 오류, 서버 거부
        """
        if not self.settings.checkin_ready:
            raise CheckInError('체크인 설정이 비어 있습니다. FACE_CHECKIN_WEBHOOK_SECRET / FACE_DEVICE_ID 를 확인하세요.')
        if not (student_id or attendance_no):
            raise CheckInError('student_id 또는 attendance_no 중 하나는 반드시 필요합니다.')

        # 서버는 KST 기준으로 계산하므로 단말 로컬 시각을 그대로 사용
        now = datetime.now()
        checked_in_on = checked_in_on or now.strftime('%Y-%m-%d')
        checked_in_at = checked_in_at or now.strftime('%H:%M:%S')
        idempotency_key = idempotency_key or build_idempotency_key(
            self.settings.device_id, student_id or attendance_no, checked_in_on
        )

        payload = {
            'version': PAYLOAD_VERSION,
            'device_id': self.settings.device_id,
            'checked_in_on': checked_in_on,
            'checked_in_at': checked_in_at,
            'idempotency_key': idempotency_key,
        }
        # 둘 다 있으면 둘 다 전송 (서버가 student_id 를 우선 사용)
        if student_id:
            payload['student_id'] = student_id
        if attendance_no:
            payload['attendance_no'] = attendance_no

        # 서명 대상과 전송 본문이 반드시 동일한 바이트여야 함
        raw_body = json.dumps(payload, ensure_ascii=False,
                              separators=(',', ':')).encode('utf-8')
        timestamp = str(int(time.time()))

        headers = {
            'Content-Type': 'application/json',
            'X-Webhook-Timestamp': timestamp,
            'X-Webhook-Signature': sign_payload(
                self.settings.webhook_secret, timestamp, raw_body),
        }

        url = f'{self.settings.api_base_url}{CHECKIN_PATH}'
        try:
            with self._lock:
                response = self._session.post(
                    url, data=raw_body, headers=headers,
                    timeout=self.settings.request_timeout_sec,
                )
        except requests.RequestException as exc:
            # 네트워크 오류는 재전송 대상
            raise CheckInError(f'체크인 전송 실패: {exc}', retryable=True) from exc

        try:
            body = response.json()
        except ValueError:
            body = {}

        if response.status_code >= 400:
            error = body.get('error', {}) if isinstance(body, dict) else {}
            code = error.get('code')
            message = error.get('message') or response.text[:200]
            # 5xx 는 일시적 장애일 수 있으므로 재전송 대상
            retryable = response.status_code >= 500
            raise CheckInError(
                f'체크인 거부 (HTTP {response.status_code} {code}): {message}',
                status_code=response.status_code, code=code, retryable=retryable,
            )

        data = body.get('data', body) if isinstance(body, dict) else {}
        return CheckInResult(
            outcome=data.get('outcome', 'recorded'),
            status_code=response.status_code,
            check_in_id=data.get('check_in_id'),
            student_name=data.get('student_name'),
            raw=body,
        )


_client: Optional[CheckInClient] = None
_client_lock = threading.Lock()


def get_checkin_client() -> CheckInClient:
    """CheckInClient 싱글톤 반환"""
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = CheckInClient()
    return _client
