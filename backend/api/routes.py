"""
FastAPI 라우트 정의

얼굴 인식 시스템 API 엔드포인트
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Query
from fastapi.responses import Response, StreamingResponse
from typing import List, Optional
from pydantic import BaseModel
import cv2
import numpy as np
import logging
import uuid
from datetime import datetime, date, timedelta
from utils.text_utils import put_korean_text, get_text_size

# 로컬 모듈 import
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.face_recognition import FaceRecognizer
from models.face_database import FaceDatabase
from models.liveness import LivenessDetector, SessionStatus
from camera.camera_handler import CameraHandler
from integrations.edu_manager import EduManagerError, get_edu_manager_client
from security import Principal, authenticate, require_device, require_operator
from utils.upload_limits import MAX_IMAGE_BYTES


logger = logging.getLogger(__name__)
THUMBNAIL_MAX_SIZE = 256


# ==================== Pydantic 모델 ====================

class FaceRegisterRequest(BaseModel):
    """얼굴 등록 요청 모델"""
    name: str
    metadata: Optional[dict] = None


class FaceRegisterResponse(BaseModel):
    """얼굴 등록 응답 모델"""
    success: bool
    face_id: Optional[str] = None
    name: Optional[str] = None
    message: str


class EduStudent(BaseModel):
    id: str
    name: str
    school: Optional[str] = None
    grade: Optional[str] = None

class EduStudentListResponse(BaseModel):
    students: List[EduStudent]
    total: int

class EduEnrollment(BaseModel):
    id: str
    name: str
    subject: str
    teacher: str

class EduEnrollmentListResponse(BaseModel):
    month: str
    enrollments: List[EduEnrollment]

class FaceInfo(BaseModel):
    """얼굴 정보 모델"""
    face_id: str
    name: str
    registered_at: str
    last_seen: Optional[str] = None
    recognition_count: int
    thumbnail_url: Optional[str] = None
    sample_count: int = 1  # 등록된 샘플 개수


class FaceListResponse(BaseModel):
    """얼굴 목록 응답 모델"""
    total: int
    faces: List[FaceInfo]


class FaceDeleteResponse(BaseModel):
    """얼굴 삭제 응답 모델"""
    success: bool
    face_id: str
    message: str


class FaceAddSampleResponse(BaseModel):
    """추가 샘플 등록 응답 모델"""
    success: bool
    face_id: str
    sample_count: int
    message: str


class FaceMergeResponse(BaseModel):
    """얼굴 통합 응답 모델"""
    success: bool
    merged_face_id: Optional[str] = None
    name: str
    merged_count: int
    message: str


class HealthResponse(BaseModel):
    """헬스체크 응답 모델"""
    status: str


class AuthInfoResponse(BaseModel):
    """현재 로컬 API 역할."""
    role: str


class FaceMergeRequest(BaseModel):
    """얼굴 통합 요청. 이름을 URL/접근 로그에 넣지 않습니다."""
    name: str


class AttendancePersonRequest(BaseModel):
    """개인 출석 조회 요청. 개인정보를 URL에 넣지 않습니다."""
    name: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class LivenessStatusRequest(BaseModel):
    """Liveness 상태 조회 요청. 세션 ID를 URL에 넣지 않습니다."""
    session_id: str


class RecognizedFaceInfo(BaseModel):
    """인식된 얼굴 정보 (프론트엔드 표시용)"""
    name: str
    confidence: Optional[float] = None
    age: Optional[int] = None
    gender: Optional[str] = None


class CameraStatsResponse(BaseModel):
    """카메라 통계 응답 모델"""
    faces_detected: int
    faces_recognized: int
    fps: float
    last_updated: str
    recognized_faces: List[RecognizedFaceInfo] = []
    today_attendance_count: int = 0


# ==================== 출석 관련 모델 ====================

class AttendanceRecord(BaseModel):
    """출석 기록 모델"""
    id: str
    face_id: Optional[str] = None
    name: str
    date: str
    time: str
    confidence: Optional[float] = None
    created_at: Optional[str] = None


class AttendanceListResponse(BaseModel):
    """출석 목록 응답 모델"""
    date: Optional[str] = None
    total: int
    records: List[AttendanceRecord]


class AttendanceStatsResponse(BaseModel):
    """출석 통계 응답 모델"""
    start_date: str
    end_date: str
    total_days: int
    total_records: int
    by_person: List[dict]


class AttendanceDeleteResponse(BaseModel):
    """출석 삭제 응답 모델"""
    success: bool
    message: str


# ==================== Liveness 관련 모델 ====================

class ChallengeInfo(BaseModel):
    """챌린지 정보"""
    index: int
    target_angle: float
    status: str
    expected_yaw: float
    expected_pitch: float
    last_measured_yaw: Optional[float] = None
    last_measured_pitch: Optional[float] = None


class LivenessSessionResponse(BaseModel):
    """Liveness 세션 응답"""
    session_id: str
    status: str
    current_challenge_index: int
    total_challenges: int
    passed_count: int
    challenges: List[ChallengeInfo]
    timeout: float
    elapsed: float
    face_id: Optional[str] = None
    face_name: Optional[str] = None
    motion_score: float = 0.0
    face_id_consistent: bool = True


class LivenessCheckResponse(BaseModel):
    """Liveness 검증 결과"""
    challenge_passed: bool
    session_completed: bool
    message: str
    current_challenge_index: Optional[int] = None
    total_challenges: Optional[int] = None
    yaw_diff: Optional[float] = None
    pitch_diff: Optional[float] = None
    measured_yaw: Optional[float] = None
    measured_pitch: Optional[float] = None
    expected_yaw: Optional[float] = None
    expected_pitch: Optional[float] = None
    next_target_angle: Optional[float] = None
    error: Optional[str] = None
    face_id: Optional[str] = None
    face_name: Optional[str] = None
    face_confidence: Optional[float] = None
    motion_score: Optional[float] = None


# ==================== 의존성 ====================

# 전역 인스턴스 (싱글톤)
_face_recognizer: Optional[FaceRecognizer] = None
_face_database: Optional[FaceDatabase] = None
_camera_handler: Optional[CameraHandler] = None
_liveness_detector: Optional[LivenessDetector] = None

# 출석 캐시 (당일 출석 완료된 face_id 집합, DB 조회 최소화)
_today_attendance_cache: set = set()
_cache_date: str = date.today().strftime('%Y-%m-%d')

# 실시간 통계 (카메라 스트림용)
_camera_stats = {
    'faces_detected': 0,
    'faces_recognized': 0,
    'fps': 0.0,
    'last_updated': datetime.now().isoformat(),
    'frame_count': 0,
    'start_time': datetime.now(),
    'recognized_faces': [],
    'today_attendance_count': 0
}


def get_face_recognizer() -> FaceRecognizer:
    """얼굴 인식기 의존성"""
    global _face_recognizer
    if _face_recognizer is None:
        _face_recognizer = FaceRecognizer()
    return _face_recognizer


def get_face_database() -> FaceDatabase:
    """얼굴 데이터베이스 의존성"""
    global _face_database
    if _face_database is None:
        _face_database = FaceDatabase()
    return _face_database


def get_camera_handler() -> CameraHandler:
    """카메라 핸들러 의존성"""
    global _camera_handler
    if _camera_handler is None:
        _camera_handler = CameraHandler(camera_id=0)
        _camera_handler.open()
    return _camera_handler


def get_liveness_detector() -> LivenessDetector:
    """Liveness 검출기 의존성"""
    global _liveness_detector
    if _liveness_detector is None:
        _liveness_detector = LivenessDetector(
            num_challenges=2,
            session_timeout=60.0,
            yaw_tolerance=15.0,
            pitch_tolerance=15.0,
        )
    return _liveness_detector


# ==================== 라우터 ====================

router = APIRouter(prefix="/api", tags=["face"])


def _server_error(event: str) -> HTTPException:
    """Log a non-sensitive event name and return a generic client error."""
    logger.error(event)
    return HTTPException(status_code=500, detail="Request could not be completed")


async def _read_image(file: UploadFile) -> np.ndarray:
    """Read one bounded image upload without retaining or logging its bytes."""
    contents = await file.read(MAX_IMAGE_BYTES + 1)
    if len(contents) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image is too large")

    image = cv2.imdecode(np.frombuffer(contents, np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=400, detail="Invalid image")
    return image


def _extract_enrollment_sample(image: np.ndarray, recognizer: FaceRecognizer):
    """Return one embedding and a fixed-size, metadata-free face thumbnail."""
    results = recognizer.detect_and_extract(image)
    if len(results) != 1:
        return None

    result = results[0]
    x1, y1, x2, y2 = (int(value) for value in result["bbox"])
    height, width = image.shape[:2]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(width, x2), min(height, y2)
    if x2 <= x1 or y2 <= y1:
        return None

    face_crop = image[y1:y2, x1:x2].copy()
    scale = min(
        THUMBNAIL_MAX_SIZE / face_crop.shape[1],
        THUMBNAIL_MAX_SIZE / face_crop.shape[0],
        1.0,
    )
    if scale < 1.0:
        face_crop = cv2.resize(
            face_crop,
            (
                max(1, round(face_crop.shape[1] * scale)),
                max(1, round(face_crop.shape[0] * scale)),
            ),
            interpolation=cv2.INTER_AREA,
        )
    return result["embedding"], face_crop


def _edu_error(_error: Exception) -> HTTPException:
    logger.error("edu_manager_request_failed")
    return HTTPException(status_code=503, detail="Student attendance service is unavailable")


def _monthly_enrollments(month: str) -> list[dict]:
    try:
        data = get_edu_manager_client().list_monthly_enrollments(month)
        rows = data.get("rows", [])
        if not isinstance(rows, list):
            raise EduManagerError("Edu Manager returned invalid enrollment rows")
        return rows
    except EduManagerError as error:
        raise _edu_error(error)


def _external_attendance_for_date(target_date: str) -> list[AttendanceRecord]:
    try:
        datetime.strptime(target_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date")
    day = str(int(target_date[-2:]))
    return [AttendanceRecord(id=f"{row.get('id')}:{target_date}", name=str(row.get("name", "")), date=target_date, time="-") for row in _monthly_enrollments(target_date[:7]) if (row.get("attendance") or {}).get(day)]


def _external_attendance_for_range(start_date: str, end_date: str) -> list[AttendanceRecord]:
    """Read the requested calendar interval from each relevant Edu Manager month."""
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date")
    if end < start or (end - start).days > 366:
        raise HTTPException(status_code=400, detail="Invalid attendance date range")

    records: list[AttendanceRecord] = []
    rows_by_month: dict[str, list[dict]] = {}
    current = start
    while current <= end:
        month = current.strftime("%Y-%m")
        rows = rows_by_month.get(month)
        if rows is None:
            rows = _monthly_enrollments(month)
            rows_by_month[month] = rows
        day = str(current.day)
        for row in rows:
            if (row.get("attendance") or {}).get(day):
                records.append(AttendanceRecord(
                    id=f"{row.get('id')}:{current.isoformat()}",
                    name=str(row.get("name", "")),
                    date=current.isoformat(),
                    time="-",
                ))
        current += timedelta(days=1)
    return records


# ==================== 헬스체크 ====================

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    API 헬스체크 엔드포인트

    민감한 모델/데이터베이스 정보 없이 프로세스 상태만 반환합니다.
    """
    return HealthResponse(status="healthy")


@router.get("/edu/students", response_model=EduStudentListResponse, dependencies=[Depends(require_operator)])
async def list_edu_students(q: str = Query("", max_length=100)):
    try:
        data = get_edu_manager_client().list_students(query=q.strip())
        students = [EduStudent(**student) for student in data.get("data", [])]
        return EduStudentListResponse(students=students, total=data.get("meta", {}).get("total_count", len(students)))
    except EduManagerError as error:
        raise _edu_error(error)

@router.get("/edu/enrollments", response_model=EduEnrollmentListResponse, dependencies=[Depends(require_operator)])
async def list_edu_enrollments(month: str = Query(..., pattern=r"^\d{4}-\d{2}$")):
    rows = _monthly_enrollments(month)
    return EduEnrollmentListResponse(month=month, enrollments=[EduEnrollment(**row) for row in rows])

@router.get("/auth/whoami", response_model=AuthInfoResponse)
async def auth_whoami(principal: Principal = Depends(authenticate)):
    """Validate a runtime credential and return only its local role."""
    return AuthInfoResponse(role=principal.role.value)


# ==================== 얼굴 등록 ====================

@router.post(
    "/face/register",
    response_model=FaceRegisterResponse,
    dependencies=[Depends(require_operator)],
)
async def register_face(
    name: str = Form(...),
    student_id: str = Form(...),
    enrollment_id: str = Form(...),
    file: UploadFile = File(...),
    recognizer: FaceRecognizer = Depends(get_face_recognizer),
    database: FaceDatabase = Depends(get_face_database)
):
    """
    얼굴 등록 엔드포인트

    Args:
        name: 등록할 사람의 이름
        file: 얼굴 이미지 파일 (JPEG, PNG 등)

    Returns:
        등록 결과 (성공 여부, face_id, 메시지)
    """
    try:
        normalized_name = name.strip()
        if not normalized_name or len(normalized_name) > 100 or not student_id or not enrollment_id:
            raise HTTPException(status_code=400, detail="Invalid student assignment")
        try:
            student = get_edu_manager_client().get_student(student_id)
            rows = _monthly_enrollments(datetime.now().strftime("%Y-%m"))
        except EduManagerError as error:
            raise _edu_error(error)
        if student.get("name") != normalized_name or not any(row.get("id") == enrollment_id and row.get("name") == normalized_name for row in rows):
            raise HTTPException(status_code=400, detail="Student and enrollment do not match")

        image = await _read_image(file)
        enrollment_sample = _extract_enrollment_sample(image, recognizer)
        if enrollment_sample is None:
            return FaceRegisterResponse(
                success=False,
                message="Exactly one face must be visible in the image."
            )
        embedding, thumbnail = enrollment_sample

        # 같은 이름이 이미 있는지 확인
        existing_face_id = None
        for fid, fdata in database.faces.items():
            if fdata.get('name') == normalized_name:
                existing_face_id = fid
                break

        if existing_face_id:
            # 기존 얼굴에 샘플로 추가
            success = database.add_face_sample(existing_face_id, embedding)

            if success:
                face_data = database.faces[existing_face_id]
                sample_count = face_data.get('sample_count', 1)

                return FaceRegisterResponse(
                    success=True,
                    face_id=existing_face_id,
                    name=normalized_name,
                    message="A new biometric sample was added."
                )
            else:
                return FaceRegisterResponse(
                    success=False,
                    message="샘플 추가 중 오류가 발생했습니다."
                )
        else:
            # 새로운 얼굴 등록
            # 고유 ID 생성
            face_id = f"person_{uuid.uuid4().hex}"

            # 메타데이터 구성
            metadata = {
                'name': normalized_name,
                'registered_at': datetime.now().isoformat(),
                'source': 'api',
                'student_id': student_id,
                'enrollment_id': enrollment_id
            }

            # 데이터베이스에 등록
            success = database.register_face(face_id, embedding, metadata, thumbnail)

            if success:
                return FaceRegisterResponse(
                    success=True,
                    face_id=face_id,
                    name=normalized_name,
                    message="Face registration completed."
                )
            else:
                return FaceRegisterResponse(
                    success=False,
                    message="얼굴 등록 중 오류가 발생했습니다."
                )

    except HTTPException:
        raise
    except Exception:
        raise _server_error("face_registration_failed")


# ==================== 추가 샘플 등록 ====================

@router.post(
    "/face/{face_id}/add-sample",
    response_model=FaceAddSampleResponse,
    dependencies=[Depends(require_operator)],
)
async def add_face_sample(
    face_id: str,
    file: UploadFile = File(...),
    recognizer: FaceRecognizer = Depends(get_face_recognizer),
    database: FaceDatabase = Depends(get_face_database)
):
    """
    기존 얼굴에 추가 샘플 등록 (같은 사람의 다른 사진)

    Args:
        face_id: 기존 얼굴 ID
        file: 추가할 얼굴 이미지 파일

    Returns:
        등록 결과
    """
    try:
        # 얼굴 ID 존재 여부 확인
        if face_id not in database.faces:
            raise HTTPException(status_code=404, detail=f"얼굴 ID '{face_id}'를 찾을 수 없습니다.")

        image = await _read_image(file)
        enrollment_sample = _extract_enrollment_sample(image, recognizer)
        if enrollment_sample is None:
            return FaceAddSampleResponse(
                success=False,
                face_id=face_id,
                sample_count=database.faces[face_id].get('sample_count', 1),
                message="Exactly one face must be visible in the image."
            )
        embedding, _ = enrollment_sample

        # 추가 샘플 등록
        success = database.add_face_sample(face_id, embedding)

        if success:
            face_data = database.faces[face_id]
            sample_count = face_data.get('sample_count', 1)
            name = face_data.get('name', face_id)

            return FaceAddSampleResponse(
                success=True,
                face_id=face_id,
                sample_count=sample_count,
                message="A new biometric sample was added."
            )
        else:
            raise HTTPException(status_code=500, detail="샘플 추가 중 오류가 발생했습니다.")

    except HTTPException:
        raise
    except Exception:
        raise _server_error("face_sample_add_failed")


# ==================== 얼굴 목록 조회 ====================

@router.get(
    "/faces/list",
    response_model=FaceListResponse,
    dependencies=[Depends(require_operator)],
)
async def list_faces(
    database: FaceDatabase = Depends(get_face_database)
):
    """
    등록된 모든 얼굴 목록 조회

    Returns:
        등록된 얼굴 정보 리스트
    """
    try:
        all_faces = database.get_all_faces()

        face_list = []
        for face_data in all_faces:
            thumbnail_url = None
            if database.get_thumbnail_path(face_data['face_id']) is not None:
                thumbnail_url = f"/api/faces/{face_data['face_id']}/thumbnail"

            face_info = FaceInfo(
                face_id=face_data['face_id'],
                name=face_data['name'],
                registered_at=face_data['registered_at'],
                last_seen=face_data.get('last_seen'),
                recognition_count=face_data.get('recognition_count', 0),
                thumbnail_url=thumbnail_url,
                sample_count=face_data.get('sample_count', 1)
            )
            face_list.append(face_info)

        return FaceListResponse(
            total=len(face_list),
            faces=face_list
        )

    except Exception:
        raise _server_error("face_list_failed")


@router.get(
    "/faces/{face_id}/thumbnail",
    dependencies=[Depends(require_operator)],
)
async def get_face_thumbnail(
    face_id: str,
    database: FaceDatabase = Depends(get_face_database),
):
    """Return a re-encoded, bounded thumbnail without exposing storage paths."""
    image_path = database.get_thumbnail_path(face_id)
    if image_path is None:
        raise HTTPException(status_code=404, detail="Thumbnail not found")

    image = cv2.imread(image_path, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=404, detail="Thumbnail not found")

    height, width = image.shape[:2]
    scale = min(THUMBNAIL_MAX_SIZE / width, THUMBNAIL_MAX_SIZE / height, 1.0)
    if scale < 1.0:
        image = cv2.resize(
            image,
            (max(1, round(width * scale)), max(1, round(height * scale))),
            interpolation=cv2.INTER_AREA,
        )

    encoded, buffer = cv2.imencode(
        ".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), 80]
    )
    if not encoded:
        raise _server_error("thumbnail_encoding_failed")

    return Response(
        content=buffer.tobytes(),
        media_type="image/jpeg",
        headers={
            "Cache-Control": "private, no-store",
            "Pragma": "no-cache",
            "X-Content-Type-Options": "nosniff",
            "Cross-Origin-Resource-Policy": "same-origin",
        },
    )


# ==================== 얼굴 삭제 ====================

@router.delete(
    "/face/{face_id}",
    response_model=FaceDeleteResponse,
    dependencies=[Depends(require_operator)],
)
async def delete_face(
    face_id: str,
    database: FaceDatabase = Depends(get_face_database)
):
    """
    등록된 얼굴 삭제

    Args:
        face_id: 삭제할 얼굴 ID

    Returns:
        삭제 결과
    """
    try:
        if face_id not in database.faces:
            raise HTTPException(status_code=404, detail="Face not found")

        success = database.remove_face(face_id)

        if success:
            return FaceDeleteResponse(
                success=True,
                face_id=face_id,
                message="Face data was deleted."
            )
        else:
            raise _server_error("face_deletion_failed")

    except HTTPException:
        raise
    except Exception:
        raise _server_error("face_deletion_failed")


# ==================== 얼굴 통합 ====================

@router.post(
    "/faces/merge",
    response_model=FaceMergeResponse,
    dependencies=[Depends(require_operator)],
)
async def merge_faces(
    request: FaceMergeRequest,
    database: FaceDatabase = Depends(get_face_database)
):
    """
    같은 이름을 가진 모든 얼굴을 하나로 통합

    Args:
        name: 통합할 이름

    Returns:
        통합 결과
    """
    try:
        name = request.name.strip()
        if not name or len(name) > 100:
            raise HTTPException(status_code=400, detail="Invalid name")

        # 같은 이름을 가진 얼굴 개수 확인
        matching_faces = [
            face_id for face_id, face_data in database.faces.items()
            if face_data.get('name') == name
        ]

        if len(matching_faces) <= 1:
            return FaceMergeResponse(
                success=False,
                name=name,
                merged_count=len(matching_faces),
                message=f"'{name}' 이름을 가진 얼굴이 {len(matching_faces)}개입니다. 통합할 필요가 없습니다."
            )

        # 통합 수행
        merged_face_id = database.merge_faces_by_name(name)

        if merged_face_id:
            return FaceMergeResponse(
                success=True,
                merged_face_id=merged_face_id,
                name=name,
                merged_count=len(matching_faces),
                message=f"'{name}' 이름을 가진 {len(matching_faces)}개의 얼굴이 '{merged_face_id}'로 통합되었습니다."
            )
        else:
            raise HTTPException(status_code=500, detail="얼굴 통합 중 오류가 발생했습니다.")

    except HTTPException:
        raise
    except Exception:
        raise _server_error("face_merge_failed")


# ==================== 실시간 비디오 스트리밍 ====================

def _record_attendance_if_needed(face_id: str, name: str, confidence: float) -> None:
    """
    출석 기록 처리 (캐시 + DB)

    메모리 캐시로 당일 중복 DB 조회를 방지하고,
    DB의 UNIQUE 제약조건으로 최종 방어합니다.
    """
    global _today_attendance_cache, _cache_date, _attendance_db, _camera_stats

    # 날짜 변경 감지 → 캐시 리셋
    today = date.today().strftime('%Y-%m-%d')
    if _cache_date != today:
        _today_attendance_cache = set()
        _cache_date = today

    # 이미 캐시에 있으면 스킵
    if face_id in _today_attendance_cache:
        return

    try:
        metadata = get_face_database().faces.get(face_id, {}).get("metadata", {})
        enrollment_id = metadata.get("enrollment_id")
        if not enrollment_id:
            logger.warning("attendance_student_mapping_missing")
            _today_attendance_cache.add(face_id)
            return
        value = os.getenv("EDU_MANAGER_ATTENDANCE_VALUE", "출석").strip()
        if not value or len(value) > 20:
            raise EduManagerError("Invalid attendance value")
        get_edu_manager_client().put_attendance(enrollment_id, today, value)
        _today_attendance_cache.add(face_id)
        _camera_stats['today_attendance_count'] = len(_today_attendance_cache)
        logger.info("edu_manager_attendance_recorded")
    except Exception:
        logger.error("edu_manager_attendance_record_failed")


def _format_age_gender(age, gender) -> str:
    """나이와 성별 정보를 표시 문자열로 변환"""
    if age is None and gender is None:
        return ""
    parts = []
    if gender is not None:
        parts.append("남성" if gender == 1 else "여성")
    if age is not None:
        parts.append(f"{age}세")
    return ", ".join(parts)


def generate_frames(
    recognizer: FaceRecognizer,
    database: FaceDatabase,
    camera: CameraHandler
):
    """
    실시간 비디오 스트림 생성 (제너레이터)

    MJPEG 형식으로 프레임을 인코딩하여 스트리밍
    """
    global _camera_stats

    while True:
        ret, frame = camera.read_frame()

        if not ret:
            break

        # 얼굴 감지 및 인식
        results = recognizer.detect_and_extract(frame)

        # 통계 업데이트
        _camera_stats['faces_detected'] = len(results)
        recognized_count = 0
        current_faces = []

        for face_result in results:
            bbox = face_result['bbox']
            embedding = face_result['embedding']
            age = face_result.get('age')
            gender = face_result.get('gender')
            x1, y1, x2, y2 = bbox

            # 데이터베이스에서 매칭
            match = database.recognize_face(embedding)

            if match:
                recognized_count += 1
                face_id, confidence = match
                face_data = database.faces.get(face_id)
                name = face_data['metadata'].get('name', 'Unknown') if face_data else 'Unknown'

                # 출석 기록 처리
                _record_attendance_if_needed(face_id, name, confidence)

                # 녹색 박스 (인식됨)
                color = (0, 255, 0)
                label = f"{name} ({confidence:.2f})"
            else:
                # 빨간색 박스 (미등록)
                color = (0, 0, 255)
                label = "Unknown"
                name = "Unknown"
                confidence = None

            # 나이/성별 정보 추가
            age_gender_str = _format_age_gender(age, gender)
            if age_gender_str:
                label = f"{label} {age_gender_str}"

            # 프론트엔드 표시용 얼굴 정보 수집
            gender_str = None
            if gender is not None:
                gender_str = "남성" if gender == 1 else "여성"
            current_faces.append({
                'name': name,
                'confidence': round(confidence, 2) if confidence is not None else None,
                'age': int(age) if age is not None else None,
                'gender': gender_str,
            })

            # 박스 그리기
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            # 레이블 배경 (Pillow 기반 한글 지원)
            font_size = 20
            text_w, text_h = get_text_size(label, font_size)

            cv2.rectangle(
                frame,
                (x1, y1 - text_h - 10),
                (x1 + text_w + 4, y1),
                color,
                -1
            )

            # 레이블 텍스트 (한글 지원)
            put_korean_text(
                frame,
                label,
                (x1 + 2, y1 - text_h - 6),
                font_size=font_size,
                color=(255, 255, 255),
            )

        # 통계 업데이트 (인식 성공 수 및 얼굴 상세 정보)
        _camera_stats['faces_recognized'] = recognized_count
        _camera_stats['recognized_faces'] = current_faces

        # FPS 계산
        _camera_stats['frame_count'] += 1
        elapsed = (datetime.now() - _camera_stats['start_time']).total_seconds()
        if elapsed > 0:
            _camera_stats['fps'] = _camera_stats['frame_count'] / elapsed

        _camera_stats['last_updated'] = datetime.now().isoformat()

        # JPEG로 인코딩
        ret, buffer = cv2.imencode('.jpg', frame)

        if not ret:
            continue

        frame_bytes = buffer.tobytes()

        # MJPEG 형식으로 yield
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')


@router.get(
    "/camera/stream",
    dependencies=[Depends(require_operator)],
)
async def video_stream(
    recognizer: FaceRecognizer = Depends(get_face_recognizer),
    database: FaceDatabase = Depends(get_face_database),
    camera: CameraHandler = Depends(get_camera_handler)
):
    """
    실시간 비디오 스트림 엔드포인트

    MJPEG 형식으로 실시간 얼굴 인식 비디오를 스트리밍합니다.

    Usage:
        HTML에서 <img src="/api/camera/stream">로 사용
    """
    return StreamingResponse(
        generate_frames(recognizer, database, camera),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@router.get(
    "/camera/stats",
    response_model=CameraStatsResponse,
    dependencies=[Depends(require_operator)],
)
async def get_camera_stats():
    """
    실시간 카메라 통계 조회

    Returns:
        현재 프레임의 얼굴 감지/인식 통계 및 FPS
    """
    global _camera_stats

    return CameraStatsResponse(
        faces_detected=_camera_stats['faces_detected'],
        faces_recognized=_camera_stats['faces_recognized'],
        fps=round(_camera_stats['fps'], 1),
        last_updated=_camera_stats['last_updated'],
        recognized_faces=[
            RecognizedFaceInfo(**f) for f in _camera_stats.get('recognized_faces', [])
        ],
        today_attendance_count=_camera_stats.get('today_attendance_count', 0)
    )


# ==================== 카메라 제어 ====================

@router.post("/camera/release", dependencies=[Depends(require_operator)])
async def release_camera():
    """
    카메라 리소스 해제

    얼굴 등록 페이지에서 프론트엔드 카메라를 사용하기 위해
    백엔드 카메라를 일시적으로 해제합니다.
    """
    global _camera_handler

    if _camera_handler is not None:
        _camera_handler.release()
        _camera_handler = None
        return {"success": True, "message": "카메라가 해제되었습니다."}

    return {"success": True, "message": "카메라가 이미 해제되어 있습니다."}


@router.post("/camera/reopen", dependencies=[Depends(require_operator)])
async def reopen_camera():
    """
    카메라 재시작

    대시보드로 돌아올 때 백엔드 카메라를 다시 시작합니다.
    """
    global _camera_handler

    try:
        if _camera_handler is None or not _camera_handler.is_opened:
            _camera_handler = CameraHandler(camera_id=0)
            _camera_handler.open()
            return {"success": True, "message": "카메라가 시작되었습니다."}

        return {"success": True, "message": "카메라가 이미 실행 중입니다."}

    except Exception:
        logger.error("camera_reopen_failed")
        return {"success": False, "message": "Camera could not be started."}


# ==================== 출석 API ====================

@router.get(
    "/attendance/today",
    response_model=AttendanceListResponse,
    dependencies=[Depends(require_operator)],
)
async def get_today_attendance():
    """Today's attendance, sourced from Edu Manager rather than local SQLite."""
    today = date.today().strftime('%Y-%m-%d')
    records = _external_attendance_for_date(today)
    return AttendanceListResponse(date=today, total=len(records), records=records)


@router.get(
    "/attendance/date/{target_date}",
    response_model=AttendanceListResponse,
    dependencies=[Depends(require_operator)],
)
async def get_attendance_by_date(target_date: str):
    """A date's attendance, sourced from Edu Manager."""
    records = _external_attendance_for_date(target_date)
    return AttendanceListResponse(date=target_date, total=len(records), records=records)


@router.get(
    "/attendance/range",
    response_model=AttendanceListResponse,
    dependencies=[Depends(require_operator)],
)
async def get_attendance_range(
    start_date: str = Query(..., description="시작 날짜 (YYYY-MM-DD)"),
    end_date: str = Query(..., description="종료 날짜 (YYYY-MM-DD)"),
):
    """Attendance history, sourced from Edu Manager."""
    records = _external_attendance_for_range(start_date, end_date)
    return AttendanceListResponse(total=len(records), records=records)


@router.post(
    "/attendance/person/search",
    response_model=AttendanceListResponse,
    dependencies=[Depends(require_operator)],
)
async def get_attendance_by_person(
    request: AttendancePersonRequest,
):
    """특정 인물 출석 이력 조회"""
    name = request.name.strip()
    if not name or len(name) > 100:
        raise HTTPException(status_code=400, detail="Invalid name")
    if bool(request.start_date) != bool(request.end_date):
        raise HTTPException(status_code=400, detail="Both dates are required")
    end_date = request.end_date or date.today().isoformat()
    start_date = request.start_date or (date.today() - timedelta(days=30)).isoformat()
    records = [record for record in _external_attendance_for_range(start_date, end_date) if record.name == name]
    return AttendanceListResponse(
        total=len(records),
        records=records
    )


@router.get(
    "/attendance/stats",
    response_model=AttendanceStatsResponse,
    dependencies=[Depends(require_operator)],
)
async def get_attendance_stats(
    start_date: str = Query(..., description="시작 날짜 (YYYY-MM-DD)"),
    end_date: str = Query(..., description="종료 날짜 (YYYY-MM-DD)"),
):
    """Aggregate external attendance without retaining a second local record set."""
    records = _external_attendance_for_range(start_date, end_date)
    grouped: dict[str, int] = {}
    for record in records:
        grouped[record.name] = grouped.get(record.name, 0) + 1
    return AttendanceStatsResponse(
        start_date=start_date,
        end_date=end_date,
        total_days=len({record.date for record in records}),
        total_records=len(records),
        by_person=[{"name": name, "count": count} for name, count in sorted(grouped.items())],
    )


@router.delete(
    "/attendance/{record_id}",
    response_model=AttendanceDeleteResponse,
    dependencies=[Depends(require_operator)],
)
async def delete_attendance(
    record_id: str,
):
    """Edu Manager records are edited at their source, not in a local mirror."""
    raise HTTPException(status_code=405, detail="Edit attendance in Edu Manager")


# ==================== Liveness Detection API ====================

@router.post("/liveness/start", response_model=LivenessSessionResponse)
async def start_liveness_session(
    principal: Principal = Depends(require_device),
    liveness: LivenessDetector = Depends(get_liveness_detector),
):
    """
    Liveness 검증 세션 시작

    2개의 챌린지(서로 반대 방향)를 생성하고 세션을 반환합니다.
    프론트엔드는 각 챌린지의 target_angle을 사용하여 타원 위에 점을 표시합니다.
    IP 기반 재시도 횟수를 제한합니다 (10분 내 최대 5회).

    Returns:
        세션 정보 (session_id, 챌린지 목록 등)
    """
    session, error = liveness.create_session(client_id=principal.subject)

    if error == "retry_limit_exceeded":
        raise HTTPException(
            status_code=429,
            detail="너무 많은 시도입니다. 10분 후에 다시 시도해주세요."
        )

    if session is None:
        raise HTTPException(status_code=500, detail="세션 생성에 실패했습니다.")

    info = liveness.get_session_info(
        session.session_id, owner_id=principal.subject
    )
    return LivenessSessionResponse(**info)


@router.post("/liveness/check", response_model=LivenessCheckResponse)
async def check_liveness(
    session_id: str = Form(...),
    file: UploadFile = File(...),
    principal: Principal = Depends(require_device),
    liveness: LivenessDetector = Depends(get_liveness_detector),
):
    """
    Liveness 검증: 프레임 전송 + Head Pose 검증

    프론트엔드에서 웹캠 프레임을 전송하면:
    1. 얼굴 감지 + 임베딩 추출 + Head Pose 추출
    2. 얼굴 인식 (DB 매칭)
    3. Head Pose와 현재 챌린지의 기대 방향 비교
    4. 일치하면 챌린지 통과

    Args:
        session_id: Liveness 세션 ID
        file: 웹캠 프레임 이미지

    Returns:
        검증 결과 (통과 여부, 세션 완료 여부, 측정값 등)
    """
    # Validate ownership and active state before decoding the upload or touching
    # the model/biometric store. An invalid UUID must not become an identity
    # lookup oracle for a holder of the device role.
    session = liveness.get_session(session_id, owner_id=principal.subject)
    if session is None:
        raise HTTPException(status_code=404, detail="Liveness session not found")
    if session.status == SessionStatus.EXPIRED:
        raise HTTPException(status_code=410, detail="Liveness session expired")
    if session.status != SessionStatus.ACTIVE:
        raise HTTPException(status_code=409, detail="Liveness session is not active")

    # 이미지 디코딩
    image = await _read_image(file)

    # Upload reading is an await point. Recheck state so an overlapping request
    # that just completed the session cannot make this frame record or disclose
    # a second identity.
    session = liveness.get_session(session_id, owner_id=principal.subject)
    if session is None:
        raise HTTPException(status_code=404, detail="Liveness session not found")
    if session.status == SessionStatus.EXPIRED:
        raise HTTPException(status_code=410, detail="Liveness session expired")
    if session.status != SessionStatus.ACTIVE:
        raise HTTPException(status_code=409, detail="Liveness session is not active")

    # Heavy dependencies are intentionally loaded only after both checks.
    recognizer = get_face_recognizer()
    database = get_face_database()

    # 얼굴 감지 + 임베딩 + Head Pose 추출
    results = recognizer.detect_and_extract(image)

    if not results:
        return LivenessCheckResponse(
            challenge_passed=False,
            session_completed=False,
            message="얼굴을 감지할 수 없습니다. 카메라를 확인해주세요.",
            error="no_face_detected",
        )

    # 첫 번째 얼굴 사용
    face = results[0]
    pose = face.get('pose')

    if pose is None or len(pose) < 3:
        return LivenessCheckResponse(
            challenge_passed=False,
            session_completed=False,
            message="Head Pose를 추출할 수 없습니다.",
            error="no_pose_detected",
        )

    yaw, pitch, roll = pose[0], pose[1], pose[2]

    # 얼굴 인식 (DB 매칭)
    face_id = None
    face_name = None
    face_confidence = None

    embedding = face.get('embedding')
    if embedding is not None:
        match = database.recognize_face(embedding)
        if match:
            face_id, face_confidence = match
            face_data = database.faces.get(face_id)
            if face_data:
                face_name = face_data['metadata'].get('name', 'Unknown')

    # Head Pose 검증
    result = liveness.check_pose(
        session_id=session_id,
        yaw=yaw,
        pitch=pitch,
        roll=roll,
        face_id=face_id,
        face_name=face_name,
        face_confidence=face_confidence,
        owner_id=principal.subject,
    )

    # 세션 완료 시에만 출석을 기록하고 identity를 공개합니다. Active or
    # failed challenges return no name/identifier, even though the server uses
    # recognition internally for consistency checks.
    if result.get("session_completed") and face_id and face_name:
        _record_attendance_if_needed(face_id, face_name, face_confidence or 0.0)
        result["face_id"] = face_id
        result["face_name"] = face_name
        result["face_confidence"] = (
            round(face_confidence, 2) if face_confidence is not None else None
        )

    return LivenessCheckResponse(**result)


@router.post("/liveness/status", response_model=LivenessSessionResponse)
async def get_liveness_status(
    request: LivenessStatusRequest,
    principal: Principal = Depends(require_device),
    liveness: LivenessDetector = Depends(get_liveness_detector),
):
    """
    Liveness 세션 상태 조회

    Args:
        session_id: 세션 ID

    Returns:
        세션 상태 정보
    """
    info = liveness.get_session_info(
        request.session_id, owner_id=principal.subject
    )
    if info is None:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    return LivenessSessionResponse(**info)


# ==================== 정리 함수 ====================

def cleanup_resources():
    """리소스 정리 함수 (애플리케이션 종료 시 호출)"""
    global _camera_handler

    if _camera_handler is not None:
        _camera_handler.release()
        _camera_handler = None
