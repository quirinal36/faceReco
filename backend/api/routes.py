"""
FastAPI 라우트 정의

얼굴 인식 시스템 API 엔드포인트
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import StreamingResponse
from typing import List, Optional
from pydantic import BaseModel
import cv2
import numpy as np
import io
from datetime import datetime

# 로컬 모듈 import
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.face_recognition import FaceRecognizer
from models.face_database import FaceDatabase
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


class FaceListResponse(BaseModel):
    """얼굴 목록 응답 모델"""
    total: int
    faces: List[FaceInfo]


class FaceDeleteResponse(BaseModel):
    """얼굴 삭제 응답 모델"""
    success: bool
    face_id: str
    message: str


class HealthResponse(BaseModel):
    """헬스체크 응답 모델"""
    status: str
    model_info: dict
    database_info: dict


# ==================== 의존성 ====================

# 전역 인스턴스 (싱글톤)
_face_recognizer: Optional[FaceRecognizer] = None
_face_database: Optional[FaceDatabase] = None
_camera_handler: Optional[CameraHandler] = None


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
    name: str,
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
            face_info = FaceInfo(
                face_id=face_data['face_id'],
                name=face_data['name'],
                registered_at=face_data['registered_at'],
                last_seen=face_data.get('last_seen'),
                recognition_count=face_data.get('recognition_count', 0),
                image_path=face_data.get('image_path')
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


# ==================== 실시간 비디오 스트리밍 ====================

def generate_frames(
    recognizer: FaceRecognizer,
    database: FaceDatabase,
    camera: CameraHandler
):
    """
    실시간 비디오 스트림 생성 (제너레이터)

    MJPEG 형식으로 프레임을 인코딩하여 스트리밍
    """
    while True:
        ret, frame = camera.read_frame()

        if not ret:
            break

        # 얼굴 감지 및 인식
        results = recognizer.detect_and_extract(frame)

        for bbox, embedding in results:
            x1, y1, x2, y2 = bbox

            # 데이터베이스에서 매칭
            match = database.recognize_face(embedding)

            if match:
                face_id, confidence = match
                face_data = database.faces.get(face_id)
                name = face_data['metadata'].get('name', 'Unknown') if face_data else 'Unknown'

                # 녹색 박스 (인식됨)
                color = (0, 255, 0)
                label = f"{name} ({confidence:.2f})"
            else:
                # 빨간색 박스 (미등록)
                color = (0, 0, 255)
                label = "Unknown"

            # 박스 그리기
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            # 레이블 배경
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.6
            font_thickness = 2
            text_size = cv2.getTextSize(label, font, font_scale, font_thickness)[0]

            cv2.rectangle(
                frame,
                (x1, y1 - text_size[1] - 10),
                (x1 + text_size[0], y1),
                color,
                -1
            )

            # 레이블 텍스트
            cv2.putText(
                frame,
                label,
                (x1, y1 - 5),
                font,
                font_scale,
                (255, 255, 255),
                font_thickness
            )

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


# ==================== 정리 함수 ====================

def cleanup_resources():
    """리소스 정리 함수 (애플리케이션 종료 시 호출)"""
    global _camera_handler

    if _camera_handler is not None:
        _camera_handler.release()
        _camera_handler = None
