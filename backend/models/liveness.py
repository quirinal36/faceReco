"""
Liveness Detection 모듈

Head Pose 기반 Challenge-Response 방식으로
정적 사진을 이용한 대리 출석을 방지합니다.

동작 원리:
1. 서버가 챌린지 세션을 생성하고 타원 위의 랜덤 점(A) 위치를 지정
2. 사용자가 점(A) 방향으로 고개를 돌림
3. 서버가 Head Pose(yaw, pitch)를 분석하여 방향 일치 여부 판정
4. 2회 챌린지 통과 시 liveness 인증 완료
"""

import uuid
import math
import random
import time
from typing import Optional, Dict, Tuple, List
from dataclasses import dataclass, field
from enum import Enum

import numpy as np


class ChallengeStatus(str, Enum):
    """챌린지 상태"""
    PENDING = "pending"           # 대기 중 (아직 시작 안 함)
    IN_PROGRESS = "in_progress"   # 진행 중
    PASSED = "passed"             # 통과
    FAILED = "failed"             # 실패
    EXPIRED = "expired"           # 시간 만료


class SessionStatus(str, Enum):
    """세션 상태"""
    ACTIVE = "active"             # 활성 (챌린지 진행 중)
    COMPLETED = "completed"       # 완료 (모든 챌린지 통과)
    FAILED = "failed"             # 실패
    EXPIRED = "expired"           # 시간 만료


@dataclass
class Challenge:
    """단일 챌린지 (하나의 점 방향으로 고개 돌리기)"""
    # 타원 위의 점(A) 위치 (각도, 0~360도)
    # 0=우측, 90=상단, 180=좌측, 270=하단
    target_angle: float

    # 예상되는 Head Pose 방향 (yaw, pitch) in degrees
    expected_yaw: float    # 좌우 (-: 좌, +: 우)
    expected_pitch: float  # 상하 (-: 하, +: 상)

    # 상태
    status: ChallengeStatus = ChallengeStatus.PENDING

    # 허용 오차 (degrees)
    yaw_tolerance: float = 15.0
    pitch_tolerance: float = 15.0

    # 타임스탬프
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

    # 마지막으로 측정된 Head Pose
    last_measured_yaw: Optional[float] = None
    last_measured_pitch: Optional[float] = None


@dataclass
class LivenessSession:
    """Liveness 검증 세션"""
    session_id: str
    challenges: List[Challenge]
    current_challenge_index: int = 0
    status: SessionStatus = SessionStatus.ACTIVE
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

    # 세션 타임아웃 (초)
    timeout: float = 60.0

    # 인식된 face_id (얼굴 인식 결과)
    face_id: Optional[str] = None
    face_name: Optional[str] = None
    face_confidence: Optional[float] = None

    def is_expired(self) -> bool:
        """세션 만료 여부"""
        return time.time() - self.created_at > self.timeout

    @property
    def current_challenge(self) -> Optional[Challenge]:
        """현재 진행 중인 챌린지"""
        if self.current_challenge_index < len(self.challenges):
            return self.challenges[self.current_challenge_index]
        return None

    @property
    def passed_count(self) -> int:
        """통과한 챌린지 수"""
        return sum(1 for c in self.challenges if c.status == ChallengeStatus.PASSED)

    @property
    def total_challenges(self) -> int:
        """전체 챌린지 수"""
        return len(self.challenges)


class LivenessDetector:
    """
    Head Pose 기반 Liveness Detection

    InsightFace의 pose 속성을 활용하여
    사용자의 머리 방향이 지정된 점(A) 방향과 일치하는지 검증합니다.
    """

    # 타원 위의 점 → Head Pose 매핑
    # 타원 위의 각도에 따라 예상되는 yaw/pitch 값
    # 사용자가 화면의 특정 점을 바라보면 고개가 해당 방향으로 기울어짐
    #
    # 화면 좌표 기준:
    #   우측 상단 → yaw 양수 (오른쪽), pitch 양수 (위)
    #   좌측 하단 → yaw 음수 (왼쪽), pitch 음수 (아래)

    # 챌린지 영역 정의 (타원 위의 구간)
    CHALLENGE_ZONES = {
        "upper_right": {"angle_range": (315, 45), "yaw": 15.0, "pitch": 12.0},
        "upper_left":  {"angle_range": (135, 225), "yaw": -15.0, "pitch": 12.0},
        "lower_right": {"angle_range": (270, 315), "yaw": 15.0, "pitch": -12.0},
        "lower_left":  {"angle_range": (225, 270), "yaw": -15.0, "pitch": -12.0},
        "right":       {"angle_range": (315, 45), "yaw": 20.0, "pitch": 0.0},
        "left":        {"angle_range": (135, 225), "yaw": -20.0, "pitch": 0.0},
    }

    def __init__(
        self,
        num_challenges: int = 2,
        session_timeout: float = 60.0,
        yaw_tolerance: float = 15.0,
        pitch_tolerance: float = 15.0,
        max_sessions: int = 100,
    ):
        """
        Args:
            num_challenges: 통과해야 할 챌린지 수
            session_timeout: 세션 타임아웃 (초)
            yaw_tolerance: yaw 허용 오차 (degrees)
            pitch_tolerance: pitch 허용 오차 (degrees)
            max_sessions: 최대 동시 세션 수
        """
        self.num_challenges = num_challenges
        self.session_timeout = session_timeout
        self.yaw_tolerance = yaw_tolerance
        self.pitch_tolerance = pitch_tolerance
        self.max_sessions = max_sessions

        # 활성 세션 저장소
        self._sessions: Dict[str, LivenessSession] = {}

    def create_session(self) -> LivenessSession:
        """
        새 liveness 검증 세션 생성

        Returns:
            LivenessSession: 생성된 세션
        """
        # 만료된 세션 정리
        self._cleanup_expired_sessions()

        # 세션 ID 생성
        session_id = str(uuid.uuid4())

        # 랜덤 챌린지 생성 (서로 다른 방향)
        challenges = self._generate_challenges()

        session = LivenessSession(
            session_id=session_id,
            challenges=challenges,
            timeout=self.session_timeout,
        )

        # 첫 번째 챌린지를 진행 중으로 설정
        if challenges:
            challenges[0].status = ChallengeStatus.IN_PROGRESS

        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[LivenessSession]:
        """세션 조회"""
        session = self._sessions.get(session_id)
        if session and session.is_expired():
            session.status = SessionStatus.EXPIRED
            for c in session.challenges:
                if c.status in (ChallengeStatus.PENDING, ChallengeStatus.IN_PROGRESS):
                    c.status = ChallengeStatus.EXPIRED
        return session

    def check_pose(
        self,
        session_id: str,
        yaw: float,
        pitch: float,
        roll: float,
        face_id: Optional[str] = None,
        face_name: Optional[str] = None,
        face_confidence: Optional[float] = None,
    ) -> Dict:
        """
        Head Pose를 검증하여 현재 챌린지 통과 여부를 판정

        Args:
            session_id: 세션 ID
            yaw: 측정된 yaw 값 (좌우 회전, degrees)
            pitch: 측정된 pitch 값 (상하 회전, degrees)
            roll: 측정된 roll 값 (기울기, degrees) - 참고용
            face_id: 인식된 얼굴 ID (optional)
            face_name: 인식된 이름 (optional)
            face_confidence: 인식 신뢰도 (optional)

        Returns:
            Dict: 검증 결과
                - challenge_passed: 현재 챌린지 통과 여부
                - session_completed: 모든 챌린지 완료 여부
                - message: 결과 메시지
                - current_challenge_index: 현재 챌린지 인덱스
                - yaw_diff: yaw 차이
                - pitch_diff: pitch 차이
        """
        session = self.get_session(session_id)
        if session is None:
            return {
                "challenge_passed": False,
                "session_completed": False,
                "message": "세션을 찾을 수 없습니다.",
                "error": "session_not_found",
            }

        if session.status == SessionStatus.EXPIRED:
            return {
                "challenge_passed": False,
                "session_completed": False,
                "message": "세션이 만료되었습니다. 다시 시작해주세요.",
                "error": "session_expired",
            }

        if session.status == SessionStatus.COMPLETED:
            return {
                "challenge_passed": True,
                "session_completed": True,
                "message": "이미 완료된 세션입니다.",
            }

        if session.status == SessionStatus.FAILED:
            return {
                "challenge_passed": False,
                "session_completed": False,
                "message": "실패한 세션입니다. 다시 시작해주세요.",
                "error": "session_failed",
            }

        # 얼굴 정보 업데이트
        if face_id:
            session.face_id = face_id
        if face_name:
            session.face_name = face_name
        if face_confidence:
            session.face_confidence = face_confidence

        # 현재 챌린지 가져오기
        challenge = session.current_challenge
        if challenge is None:
            return {
                "challenge_passed": False,
                "session_completed": False,
                "message": "진행할 챌린지가 없습니다.",
                "error": "no_challenge",
            }

        # 측정값 기록
        challenge.last_measured_yaw = yaw
        challenge.last_measured_pitch = pitch

        # 방향 일치 검증
        yaw_diff = abs(yaw - challenge.expected_yaw)
        pitch_diff = abs(pitch - challenge.expected_pitch)

        challenge_passed = (
            yaw_diff <= challenge.yaw_tolerance and
            pitch_diff <= challenge.pitch_tolerance
        )

        result = {
            "challenge_passed": challenge_passed,
            "session_completed": False,
            "current_challenge_index": session.current_challenge_index,
            "total_challenges": session.total_challenges,
            "yaw_diff": round(yaw_diff, 1),
            "pitch_diff": round(pitch_diff, 1),
            "measured_yaw": round(yaw, 1),
            "measured_pitch": round(pitch, 1),
            "expected_yaw": challenge.expected_yaw,
            "expected_pitch": challenge.expected_pitch,
        }

        if challenge_passed:
            challenge.status = ChallengeStatus.PASSED
            challenge.completed_at = time.time()

            # 다음 챌린지로 이동
            session.current_challenge_index += 1

            if session.current_challenge_index >= session.total_challenges:
                # 모든 챌린지 통과
                session.status = SessionStatus.COMPLETED
                session.completed_at = time.time()
                result["session_completed"] = True
                result["message"] = "Liveness 검증 완료! 출석이 인정됩니다."
            else:
                # 다음 챌린지 시작
                next_challenge = session.current_challenge
                if next_challenge:
                    next_challenge.status = ChallengeStatus.IN_PROGRESS
                result["message"] = (
                    f"챌린지 {session.current_challenge_index}/{session.total_challenges} 통과! "
                    f"다음 방향으로 고개를 돌려주세요."
                )
                result["next_target_angle"] = next_challenge.target_angle if next_challenge else None
        else:
            result["message"] = "고개를 조금 더 돌려주세요."

        return result

    def extract_head_pose(self, face_result: dict) -> Optional[Tuple[float, float, float]]:
        """
        InsightFace 결과에서 Head Pose (yaw, pitch, roll) 추출

        Args:
            face_result: InsightFace의 face 객체 또는 detect_and_extract 결과

        Returns:
            Tuple[yaw, pitch, roll] in degrees, 또는 None
        """
        # InsightFace face 객체에서 pose 추출
        pose = face_result.get('pose')
        if pose is not None:
            if isinstance(pose, (list, tuple, np.ndarray)) and len(pose) >= 3:
                return float(pose[0]), float(pose[1]), float(pose[2])

        return None

    def _generate_challenges(self) -> List[Challenge]:
        """
        서로 다른 방향의 랜덤 챌린지 생성

        2개의 챌린지: 서로 반대 방향 (예: 우측상단 → 좌측하단)
        """
        # 대각선 반대 방향 쌍
        opposite_pairs = [
            ("upper_right", "lower_left"),
            ("upper_left", "lower_right"),
            ("right", "left"),
        ]

        # 랜덤으로 한 쌍 선택
        pair = random.choice(opposite_pairs)
        zones = [self.CHALLENGE_ZONES[pair[0]], self.CHALLENGE_ZONES[pair[1]]]

        challenges = []
        for zone in zones[:self.num_challenges]:
            # 타원 위의 각도 (구간 내 랜덤)
            angle_start, angle_end = zone["angle_range"]
            if angle_start > angle_end:
                # 예: 315~45도 (0도를 넘는 경우)
                target_angle = random.uniform(angle_start, angle_end + 360) % 360
            else:
                target_angle = random.uniform(angle_start, angle_end)

            challenge = Challenge(
                target_angle=round(target_angle, 1),
                expected_yaw=zone["yaw"],
                expected_pitch=zone["pitch"],
                yaw_tolerance=self.yaw_tolerance,
                pitch_tolerance=self.pitch_tolerance,
            )
            challenges.append(challenge)

        return challenges

    def _cleanup_expired_sessions(self):
        """만료된 세션 정리"""
        now = time.time()
        expired_ids = [
            sid for sid, session in self._sessions.items()
            if now - session.created_at > session.timeout * 2  # 타임아웃의 2배 후 삭제
        ]
        for sid in expired_ids:
            del self._sessions[sid]

        # 최대 세션 수 초과 시 가장 오래된 세션 삭제
        if len(self._sessions) > self.max_sessions:
            sorted_sessions = sorted(
                self._sessions.items(),
                key=lambda x: x[1].created_at
            )
            for sid, _ in sorted_sessions[:len(self._sessions) - self.max_sessions]:
                del self._sessions[sid]

    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """
        세션 상태 정보를 딕셔너리로 반환 (API 응답용)
        """
        session = self.get_session(session_id)
        if session is None:
            return None

        challenges_info = []
        for i, c in enumerate(session.challenges):
            info = {
                "index": i,
                "target_angle": c.target_angle,
                "status": c.status.value,
                "expected_yaw": c.expected_yaw,
                "expected_pitch": c.expected_pitch,
            }
            if c.last_measured_yaw is not None:
                info["last_measured_yaw"] = round(c.last_measured_yaw, 1)
                info["last_measured_pitch"] = round(c.last_measured_pitch, 1)
            challenges_info.append(info)

        return {
            "session_id": session.session_id,
            "status": session.status.value,
            "current_challenge_index": session.current_challenge_index,
            "total_challenges": session.total_challenges,
            "passed_count": session.passed_count,
            "challenges": challenges_info,
            "timeout": session.timeout,
            "elapsed": round(time.time() - session.created_at, 1),
            "face_id": session.face_id,
            "face_name": session.face_name,
        }
