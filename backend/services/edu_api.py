"""
edu-manager 읽기 API 클라이언트

Bearer 토큰 인증이 필요한 `/api/v1/*` 엔드포인트를 호출합니다.
- 토큰은 Supabase password grant 로 발급 (유효기간 1시간)
- 만료 60초 전 선제 갱신, 401 응답 시 1회 refresh 후 재시도
- 네트워크 실패는 EduApiError 로 정규화 (호출측에서 degraded 처리)
"""

import threading
import time
from typing import Any, Dict, List, Optional

import requests

from config import Settings, get_settings

# 만료 몇 초 전에 미리 갱신할지
TOKEN_REFRESH_MARGIN_SEC = 60


class EduApiError(Exception):
    """edu-manager API 호출 실패"""

    def __init__(self, message: str, status_code: Optional[int] = None,
                 code: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code


class EduApiClient:
    """edu-manager 읽기 API 클라이언트 (스레드 안전)"""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self._session = requests.Session()
        self._lock = threading.Lock()
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._expires_at: float = 0.0

    # ==================== 토큰 관리 ====================

    def _token_endpoint(self, grant_type: str) -> str:
        return f"{self.settings.supabase_url}/auth/v1/token?grant_type={grant_type}"

    def _store_token(self, payload: Dict[str, Any]) -> None:
        self._access_token = payload.get('access_token')
        self._refresh_token = payload.get('refresh_token') or self._refresh_token
        expires_in = payload.get('expires_in', 3600)
        try:
            expires_in = int(expires_in)
        except (TypeError, ValueError):
            expires_in = 3600
        self._expires_at = time.time() + expires_in

    def _login(self) -> None:
        """이메일/비밀번호로 신규 토큰 발급"""
        try:
            response = self._session.post(
                self._token_endpoint('password'),
                json={
                    'email': self.settings.login_email,
                    'password': self.settings.login_password,
                },
                headers={
                    'apikey': self.settings.supabase_anon_key,
                    'Content-Type': 'application/json',
                },
                timeout=self.settings.request_timeout_sec,
            )
        except requests.RequestException as exc:
            raise EduApiError(f"토큰 발급 요청 실패: {exc}") from exc

        if response.status_code != 200:
            raise EduApiError(
                f"로그인 실패 (HTTP {response.status_code}): {response.text[:200]}",
                status_code=response.status_code,
            )
        self._store_token(response.json())

    def _refresh(self) -> None:
        """refresh_token 으로 토큰 갱신 (실패 시 재로그인)"""
        if not self._refresh_token:
            self._login()
            return

        try:
            response = self._session.post(
                self._token_endpoint('refresh_token'),
                json={'refresh_token': self._refresh_token},
                headers={
                    'apikey': self.settings.supabase_anon_key,
                    'Content-Type': 'application/json',
                },
                timeout=self.settings.request_timeout_sec,
            )
        except requests.RequestException:
            self._login()
            return

        if response.status_code != 200:
            # refresh 토큰이 만료/무효면 재로그인
            self._refresh_token = None
            self._login()
            return
        self._store_token(response.json())

    def _get_access_token(self, force_refresh: bool = False) -> str:
        """유효한 access token 반환 (필요 시 발급/갱신)"""
        with self._lock:
            if force_refresh:
                self._refresh()
            elif not self._access_token:
                self._login()
            elif time.time() >= self._expires_at - TOKEN_REFRESH_MARGIN_SEC:
                self._refresh()

            if not self._access_token:
                raise EduApiError("access token 을 확보하지 못했습니다.")
            return self._access_token

    # ==================== 요청 ====================

    def _request(self, method: str, path: str,
                 params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """인증 헤더를 붙여 요청하고 JSON 본문을 반환 (401 시 1회 재시도)"""
        if not self.settings.read_api_ready:
            raise EduApiError("edu-manager 읽기 API 설정이 비어 있습니다. .env 를 확인하세요.")

        url = f"{self.settings.api_base_url}{path}"

        for attempt in (0, 1):
            token = self._get_access_token(force_refresh=(attempt == 1))
            try:
                response = self._session.request(
                    method, url,
                    params=params,
                    headers={
                        'Authorization': f'Bearer {token}',
                        'X-Organization-Id': self.settings.org_id,
                        'Accept': 'application/json',
                    },
                    timeout=self.settings.request_timeout_sec,
                )
            except requests.RequestException as exc:
                raise EduApiError(f"{method} {path} 요청 실패: {exc}") from exc

            if response.status_code == 401 and attempt == 0:
                continue  # 토큰 갱신 후 1회 재시도

            if response.status_code >= 400:
                code, message = None, response.text[:200]
                try:
                    error = response.json().get('error', {})
                    code = error.get('code')
                    message = error.get('message', message)
                except ValueError:
                    pass
                raise EduApiError(
                    f"{method} {path} 실패 (HTTP {response.status_code}): {message}",
                    status_code=response.status_code,
                    code=code,
                )

            try:
                return response.json()
            except ValueError as exc:
                raise EduApiError(f"{method} {path} 응답이 JSON 이 아닙니다.") from exc

        raise EduApiError(f"{method} {path} 실패: 재시도 한도 초과")

    # ==================== 엔드포인트 ====================

    def get_today_attendance(self, target_date: Optional[str] = None) -> Dict[str, Any]:
        """
        오늘(또는 지정일) 출석 현황 조회

        Args:
            target_date: YYYY-MM-DD (생략 시 서버 기준 오늘)

        Returns:
            { date, weekday, expectedCount, checkedInCount, rows: [...], extras: [...] }
        """
        params = {'date': target_date} if target_date else None
        payload = self._request('GET', '/api/v1/attendance/today', params=params)
        return payload.get('data', {})

    def search_students(self, query: str, page_size: int = 20) -> List[Dict[str, Any]]:
        """
        학생 검색 (이름 / 학교 / 출석번호)

        Args:
            query: 검색어
            page_size: 최대 결과 수

        Returns:
            학생 객체 리스트
        """
        payload = self._request('GET', '/api/v1/students',
                                params={'q': query, 'page_size': page_size})
        return payload.get('data', [])

    def get_classes(self, is_active: bool = True) -> List[Dict[str, Any]]:
        """활성 수업 목록 조회"""
        payload = self._request('GET', '/api/v1/classes',
                                params={'is_active': str(is_active).lower()})
        return payload.get('data', [])


# 모듈 레벨 싱글톤
_client: Optional[EduApiClient] = None
_client_lock = threading.Lock()


def get_edu_api_client() -> EduApiClient:
    """EduApiClient 싱글톤 반환"""
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = EduApiClient()
    return _client
