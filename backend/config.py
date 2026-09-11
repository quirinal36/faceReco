"""
환경 설정 모듈

프로젝트 루트의 `.env` 파일을 읽어 edu-manager API 연동 설정을 제공합니다.
외부 의존성(python-dotenv) 없이 동작하도록 최소한의 파서를 직접 구현합니다.

자격증명이 비어 있으면 연동 기능은 자동으로 비활성화되고,
기존 로컬 전용 동작(로컬 SQLite 출석 기록)만 유지됩니다.
"""

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

# 프로젝트 루트 (backend/ 의 상위 디렉토리)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOTENV_PATH = os.path.join(PROJECT_ROOT, '.env')


def load_dotenv(path: str = DOTENV_PATH, override: bool = False) -> int:
    """
    .env 파일을 읽어 os.environ 에 반영합니다.

    Args:
        path: .env 파일 경로
        override: True면 이미 설정된 환경변수도 덮어씀

    Returns:
        읽어들인 키 개수
    """
    if not os.path.isfile(path):
        return 0

    count = 0
    with open(path, 'r', encoding='utf-8') as f:
        for raw_line in f:
            line = raw_line.strip()
            # 빈 줄 / 주석 건너뛰기
            if not line or line.startswith('#'):
                continue
            if line.startswith('export '):
                line = line[len('export '):].strip()
            if '=' not in line:
                continue

            key, _, value = line.partition('=')
            key = key.strip()
            value = value.strip()

            # 따옴표로 감싼 값 처리
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]

            if not key:
                continue
            if override or key not in os.environ:
                os.environ[key] = value
                count += 1
    return count


def _env(key: str, default: str = '') -> str:
    return os.environ.get(key, default).strip()


def _env_int(key: str, default: int) -> int:
    try:
        return int(_env(key, str(default)))
    except ValueError:
        return default


def _env_bool(key: str, default: bool) -> bool:
    value = _env(key, 'true' if default else 'false').lower()
    return value in ('1', 'true', 'yes', 'on')


@dataclass(frozen=True)
class Settings:
    """edu-manager API 연동 설정"""

    # 읽기 API (Bearer 인증)
    api_base_url: str
    org_id: str

    # 토큰 발급 (Supabase password grant)
    supabase_url: str
    supabase_anon_key: str
    login_email: str
    login_password: str

    # 체크인 전송 (HMAC 서명)
    webhook_secret: str
    device_id: str

    # 동작 설정
    checkin_enabled: bool
    roster_refresh_sec: int
    prompt_timeout_sec: int
    prompt_cooldown_sec: int

    # 네트워크
    request_timeout_sec: int = 10

    @property
    def read_api_ready(self) -> bool:
        """명단/학생 조회(Bearer 인증)에 필요한 값이 모두 있는지"""
        return all([
            self.api_base_url, self.org_id, self.supabase_url,
            self.supabase_anon_key, self.login_email, self.login_password,
        ])

    @property
    def checkin_ready(self) -> bool:
        """서버로 출석 전송(HMAC)에 필요한 값이 모두 있는지"""
        return bool(self.checkin_enabled and self.webhook_secret and self.device_id)

    def missing_keys(self) -> list:
        """비어 있는 필수 설정 키 목록 (진단용)"""
        required = {
            'EDU_API_BASE_URL': self.api_base_url,
            'EDU_ORG_ID': self.org_id,
            'EDU_SUPABASE_URL': self.supabase_url,
            'EDU_SUPABASE_ANON_KEY': self.supabase_anon_key,
            'EDU_LOGIN_EMAIL': self.login_email,
            'EDU_LOGIN_PASSWORD': self.login_password,
            'FACE_CHECKIN_WEBHOOK_SECRET': self.webhook_secret,
            'FACE_DEVICE_ID': self.device_id,
        }
        return [key for key, value in required.items() if not value]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """설정 싱글톤 (최초 호출 시 .env 로딩)"""
    load_dotenv()
    return Settings(
        api_base_url=_env('EDU_API_BASE_URL').rstrip('/'),
        org_id=_env('EDU_ORG_ID'),
        supabase_url=_env('EDU_SUPABASE_URL').rstrip('/'),
        supabase_anon_key=_env('EDU_SUPABASE_ANON_KEY'),
        login_email=_env('EDU_LOGIN_EMAIL'),
        login_password=_env('EDU_LOGIN_PASSWORD'),
        webhook_secret=_env('FACE_CHECKIN_WEBHOOK_SECRET'),
        device_id=_env('FACE_DEVICE_ID'),
        checkin_enabled=_env_bool('CHECKIN_ENABLED', True),
        roster_refresh_sec=_env_int('ROSTER_REFRESH_SEC', 60),
        prompt_timeout_sec=_env_int('PROMPT_TIMEOUT_SEC', 20),
        prompt_cooldown_sec=_env_int('PROMPT_COOLDOWN_SEC', 300),
        request_timeout_sec=_env_int('EDU_REQUEST_TIMEOUT_SEC', 10),
    )
