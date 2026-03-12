"""
FastAPI 라우트 정의

얼굴 인식 시스템 API 엔드포인트
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Query, Request
from fastapi.responses import StreamingResponse
from typing import List, Optional
from pydantic import BaseModel
import cv2
import numpy as np
import io
from datetime import datetime, date, timedelta
from PIL import ImageFont, ImageDraw, Image
from utils.text_utils import put_korean_text, get_text_size

# 로컬 모듈 import
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.face_recognition import FaceRecognizer
from models.face_database import FaceDatabase
from models.attendance_db import AttendanceDB
from models.liveness import LivenessDetector
from camera.camera_handler import CameraHandler


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


class FaceInfo(BaseModel):
    """얼굴 정보 모델"""
    face_id: str
    name: str
    registered_at: str
    last_seen: Optional[str] = None
    recognition_count: int
    image_path: Optional[str] = None
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
    model_info: dict
    database_info: dict


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
    id: int
    face_id: str
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
_attendance_db: Optional[AttendanceDB] = None
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


def get_attendance_db() -> AttendanceDB:
    """출석 데이터베이스 의존성"""
    global _attendance_db
    if _attendance_db is None:
        _attendance_db = AttendanceDB()
    return _attendance_db


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


# ==================== 헬스체크 ====================

@router.get("/health", response_model=HealthResponse)
async def health_check(
    recognizer: FaceRecognizer = Depends(get_face_recognizer),
    database: FaceDatabase = Depends(get_face_database)
):
    """
    API 헬스체크 엔드포인트

    시스템 상태, 모델 정보, 데이터베이스 정보를 반환합니다.
    """
    return HealthResponse(
        status="healthy",
        model_info=recognizer.get_model_info(),
        database_info=database.get_statistics()
    )


# ==================== 얼굴 등록 ====================

@router.post("/face/register", response_model=FaceRegisterResponse)
async def register_face(
    name: str = Form(...),
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
        # 이미지 파일 읽기
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if image is None:
            raise HTTPException(status_code=400, detail="유효하지 않은 이미지 파일입니다.")

        # 얼굴 임베딩 추출
        embedding = recognizer.extract_embedding(image)

        if embedding is None:
            return FaceRegisterResponse(
                success=False,
                message="이미지에서 얼굴을 감지할 수 없습니다. 다른 이미지를 시도해주세요."
            )

        # 같은 이름이 이미 있는지 확인
        existing_face_id = None
        for fid, fdata in database.faces.items():
            if fdata.get('name') == name:
                existing_face_id = fid
                break

        if existing_face_id:
            # 기존 얼굴에 샘플로 추가
            success = database.add_face_sample(existing_face_id, embedding, image)

            if success:
                face_data = database.faces[existing_face_id]
                sample_count = face_data.get('sample_count', 1)

                return FaceRegisterResponse(
                    success=True,
                    face_id=existing_face_id,
                    name=name,
                    message=f"'{name}'님의 {sample_count}번째 샘플이 추가되었습니다. (자동 통합)"
                )
            else:
                return FaceRegisterResponse(
                    success=False,
                    message="샘플 추가 중 오류가 발생했습니다."
                )
        else:
            # 새로운 얼굴 등록
            # 고유 ID 생성
            face_id = f"person_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # 메타데이터 구성
            metadata = {
                'name': name,
                'registered_at': datetime.now().isoformat(),
                'source': 'api'
            }

            # 데이터베이스에 등록
            success = database.register_face(face_id, embedding, metadata, image)

            if success:
                return FaceRegisterResponse(
                    success=True,
                    face_id=face_id,
                    name=name,
                    message=f"'{name}' 얼굴이 성공적으로 등록되었습니다."
                )
            else:
                return FaceRegisterResponse(
                    success=False,
                    message="얼굴 등록 중 오류가 발생했습니다."
                )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")


# ==================== 추가 샘플 등록 ====================

@router.post("/face/{face_id}/add-sample", response_model=FaceAddSampleResponse)
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

        # 이미지 파일 읽기
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if image is None:
            raise HTTPException(status_code=400, detail="유효하지 않은 이미지 파일입니다.")

        # 얼굴 임베딩 추출
        embedding = recognizer.extract_embedding(image)

        if embedding is None:
            return FaceAddSampleResponse(
                success=False,
                face_id=face_id,
                sample_count=database.faces[face_id].get('sample_count', 1),
                message="이미지에서 얼굴을 감지할 수 없습니다. 다른 이미지를 시도해주세요."
            )

        # 추가 샘플 등록
        success = database.add_face_sample(face_id, embedding, image)

        if success:
            face_data = database.faces[face_id]
            sample_count = face_data.get('sample_count', 1)
            name = face_data.get('name', face_id)

            return FaceAddSampleResponse(
                success=True,
                face_id=face_id,
                sample_count=sample_count,
                message=f"'{name}'에 {sample_count}번째 샘플이 추가되었습니다."
            )
        else:
            raise HTTPException(status_code=500, detail="샘플 추가 중 오류가 발생했습니다.")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")


# ==================== 얼굴 목록 조회 ====================

@router.get("/faces/list", response_model=FaceListResponse)
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
            # image_path를 웹 URL로 변환
            image_path = face_data.get('image_path')
            if image_path:
                # 'faces/person_xxx.jpg' -> '/data/faces/person_xxx.jpg'
                image_path = f"/data/{image_path}"

            face_info = FaceInfo(
                face_id=face_data['face_id'],
                name=face_data['name'],
                registered_at=face_data['registered_at'],
                last_seen=face_data.get('last_seen'),
                recognition_count=face_data.get('recognition_count', 0),
                image_path=image_path,
                sample_count=face_data.get('sample_count', 1)
            )
            face_list.append(face_info)

        return FaceListResponse(
            total=len(face_list),
            faces=face_list
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")


# ==================== 얼굴 삭제 ====================

@router.delete("/face/{face_id}", response_model=FaceDeleteResponse)
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
        success = database.remove_face(face_id)

        if success:
            return FaceDeleteResponse(
                success=True,
                face_id=face_id,
                message=f"얼굴 ID '{face_id}'가 성공적으로 삭제되었습니다."
            )
        else:
            raise HTTPException(status_code=404, detail=f"얼굴 ID '{face_id}'를 찾을 수 없습니다.")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")


# ==================== 얼굴 통합 ====================

@router.post("/faces/merge/{name}", response_model=FaceMergeResponse)
async def merge_faces(
    name: str,
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")


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

    # DB에 출석 기록
    try:
        attendance_db = get_attendance_db()
        recorded = attendance_db.record_attendance(face_id, name, confidence)
        # 캐시에 추가 (DB 기록 성공 여부와 관계없이, 이미 기록된 경우도 포함)
        _today_attendance_cache.add(face_id)
        if recorded:
            _camera_stats['today_attendance_count'] = attendance_db.get_today_count()
            print(f"출석 기록: {name} ({face_id}) - 신뢰도: {confidence:.2f}")
    except Exception as e:
        print(f"출석 기록 실패: {str(e)}")


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


@router.get("/camera/stream")
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


@router.get("/camera/stats", response_model=CameraStatsResponse)
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

@router.post("/camera/release")
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


@router.post("/camera/reopen")
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

    except Exception as e:
        return {"success": False, "message": f"카메라 시작 실패: {str(e)}"}


# ==================== 출석 API ====================

@router.get("/attendance/today", response_model=AttendanceListResponse)
async def get_today_attendance(
    attendance_db: AttendanceDB = Depends(get_attendance_db)
):
    """오늘 출석 현황 조회"""
    records = attendance_db.get_today_attendance()
    today = date.today().strftime('%Y-%m-%d')
    return AttendanceListResponse(
        date=today,
        total=len(records),
        records=[AttendanceRecord(**r) for r in records]
    )


@router.get("/attendance/date/{target_date}", response_model=AttendanceListResponse)
async def get_attendance_by_date(
    target_date: str,
    attendance_db: AttendanceDB = Depends(get_attendance_db)
):
    """특정 날짜 출석 조회"""
    try:
        datetime.strptime(target_date, '%Y-%m-%d')
    except ValueError:
        raise HTTPException(status_code=400, detail="날짜 형식이 올바르지 않습니다. (YYYY-MM-DD)")

    records = attendance_db.get_attendance_by_date(target_date)
    return AttendanceListResponse(
        date=target_date,
        total=len(records),
        records=[AttendanceRecord(**r) for r in records]
    )


@router.get("/attendance/range", response_model=AttendanceListResponse)
async def get_attendance_range(
    start_date: str = Query(..., description="시작 날짜 (YYYY-MM-DD)"),
    end_date: str = Query(..., description="종료 날짜 (YYYY-MM-DD)"),
    attendance_db: AttendanceDB = Depends(get_attendance_db)
):
    """기간별 출석 조회"""
    try:
        datetime.strptime(start_date, '%Y-%m-%d')
        datetime.strptime(end_date, '%Y-%m-%d')
    except ValueError:
        raise HTTPException(status_code=400, detail="날짜 형식이 올바르지 않습니다. (YYYY-MM-DD)")

    records = attendance_db.get_attendance_range(start_date, end_date)
    return AttendanceListResponse(
        total=len(records),
        records=[AttendanceRecord(**r) for r in records]
    )


@router.get("/attendance/person/{name}", response_model=AttendanceListResponse)
async def get_attendance_by_person(
    name: str,
    start_date: Optional[str] = Query(None, description="시작 날짜 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="종료 날짜 (YYYY-MM-DD)"),
    attendance_db: AttendanceDB = Depends(get_attendance_db)
):
    """특정 인물 출석 이력 조회"""
    records = attendance_db.get_attendance_by_name(name, start_date, end_date)
    return AttendanceListResponse(
        total=len(records),
        records=[AttendanceRecord(**r) for r in records]
    )


@router.get("/attendance/stats", response_model=AttendanceStatsResponse)
async def get_attendance_stats(
    start_date: str = Query(..., description="시작 날짜 (YYYY-MM-DD)"),
    end_date: str = Query(..., description="종료 날짜 (YYYY-MM-DD)"),
    attendance_db: AttendanceDB = Depends(get_attendance_db)
):
    """출석 통계 조회"""
    try:
        datetime.strptime(start_date, '%Y-%m-%d')
        datetime.strptime(end_date, '%Y-%m-%d')
    except ValueError:
        raise HTTPException(status_code=400, detail="날짜 형식이 올바르지 않습니다. (YYYY-MM-DD)")

    stats = attendance_db.get_attendance_stats(start_date, end_date)
    return AttendanceStatsResponse(**stats)


@router.delete("/attendance/{record_id}", response_model=AttendanceDeleteResponse)
async def delete_attendance(
    record_id: int,
    attendance_db: AttendanceDB = Depends(get_attendance_db)
):
    """출석 기록 삭제"""
    success = attendance_db.delete_attendance(record_id)
    if success:
        return AttendanceDeleteResponse(
            success=True,
            message=f"출석 기록 ID {record_id}가 삭제되었습니다."
        )
    else:
        raise HTTPException(status_code=404, detail=f"출석 기록 ID {record_id}를 찾을 수 없습니다.")


# ==================== Liveness Detection API ====================

@router.post("/liveness/start", response_model=LivenessSessionResponse)
async def start_liveness_session(
    request: Request,
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
    client_id = request.client.host if request.client else "unknown"
    session, error = liveness.create_session(client_id=client_id)

    if error == "retry_limit_exceeded":
        raise HTTPException(
            status_code=429,
            detail="너무 많은 시도입니다. 10분 후에 다시 시도해주세요."
        )

    if session is None:
        raise HTTPException(status_code=500, detail="세션 생성에 실패했습니다.")

    info = liveness.get_session_info(session.session_id)
    return LivenessSessionResponse(**info)


@router.post("/liveness/check", response_model=LivenessCheckResponse)
async def check_liveness(
    session_id: str = Form(...),
    file: UploadFile = File(...),
    recognizer: FaceRecognizer = Depends(get_face_recognizer),
    database: FaceDatabase = Depends(get_face_database),
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
    # 이미지 디코딩
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if image is None:
        raise HTTPException(status_code=400, detail="유효하지 않은 이미지입니다.")

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
    )

    # 세션 완료 시 출석 기록
    if result.get("session_completed") and face_id and face_name:
        _record_attendance_if_needed(face_id, face_name, face_confidence or 0.0)

    # 응답에 얼굴 정보 추가
    result["face_id"] = face_id
    result["face_name"] = face_name
    result["face_confidence"] = round(face_confidence, 2) if face_confidence else None

    return LivenessCheckResponse(**result)


@router.get("/liveness/status/{session_id}", response_model=LivenessSessionResponse)
async def get_liveness_status(
    session_id: str,
    liveness: LivenessDetector = Depends(get_liveness_detector),
):
    """
    Liveness 세션 상태 조회

    Args:
        session_id: 세션 ID

    Returns:
        세션 상태 정보
    """
    info = liveness.get_session_info(session_id)
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
