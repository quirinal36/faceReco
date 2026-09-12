"""
얼굴 인식 모듈

InsightFace를 이용한 얼굴 임베딩 추출 및 인식
"""

import cv2
import logging
import numpy as np
import os
import re
from pathlib import Path
from typing import Optional, Tuple, List, Dict
from sklearn.metrics.pairwise import cosine_similarity
from security import get_environment
from utils.text_utils import put_korean_text, get_text_size


logger = logging.getLogger(__name__)
SAFE_MODEL_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def validate_model_artifacts(model_name: Optional[str] = None) -> Optional[Path]:
    """Require locally provisioned model artifacts in production.

    InsightFace downloads missing models on first use. Production edges use an
    outbound allowlist, so startup must fail before serving traffic when the
    model bundle has not already been placed on disk.
    """
    model_root = os.getenv("FACERECO_MODEL_ROOT", "").strip()
    bundle_name = (
        model_name
        or os.getenv("FACERECO_MODEL_NAME", "").strip()
        or "buffalo_l"
    )
    if not SAFE_MODEL_NAME.fullmatch(bundle_name):
        raise RuntimeError("FACERECO_MODEL_NAME is invalid")
    production = get_environment() == "production"
    if not production:
        return Path(model_root).expanduser() if model_root else None

    root_path = Path(model_root).expanduser() if model_root else None
    bundle_path = (
        root_path / "models" / bundle_name if root_path is not None else None
    )
    provisioned = (
        root_path is not None
        and root_path.is_dir()
        and not root_path.is_symlink()
        and bundle_path is not None
        and bundle_path.is_dir()
        and not bundle_path.is_symlink()
    )
    if provisioned:
        provisioned = any(
            artifact.is_file() and not artifact.is_symlink()
            for artifact in bundle_path.glob("*.onnx")
        )
    if not provisioned:
        raise RuntimeError(
            "Production model artifacts must be provisioned before startup"
        )
    return root_path


class FaceRecognizer:
    """
    InsightFace 기반 얼굴 인식 클래스

    Attributes:
        model_name (str): 사용할 InsightFace 모델 이름
        app: InsightFace 애플리케이션 인스턴스
        device (str): 실행 디바이스 ('cuda' 또는 'cpu')
        embedding_size (int): 임베딩 벡터 크기
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
        det_size: Tuple[int, int] = (640, 640)
    ):
        """
        얼굴 인식기 초기화

        Args:
            model_name (Optional[str]): InsightFace 모델 이름 (최신 버전에서만 사용, 구버전은 None)
            device (str): 실행 디바이스. 기본값은 FACERECO_DEVICE 또는 cuda
            det_size (Tuple[int, int]): 얼굴 감지 입력 크기
        """
        self.model_name = (
            model_name
            or os.getenv("FACERECO_MODEL_NAME", "").strip()
            or "buffalo_l"
        )
        self.det_size = det_size
        production = get_environment() == "production"
        configured_root = validate_model_artifacts(self.model_name)
        model_root = str(configured_root) if configured_root is not None else ""

        def create_analysis(name: str):
            options = {"name": name}
            if model_root:
                options["root"] = str(Path(model_root).expanduser())
            return FaceAnalysis(**options)

        # InsightFace import (지연 로딩)
        try:
            from insightface.app import FaceAnalysis
        except ImportError:
            raise RuntimeError(
                "InsightFace 패키지가 설치되어 있지 않습니다. "
                "'pip install insightface onnxruntime'을 실행하세요."
            )

        # Biometric inference must use the local CUDA device.  A silent CPU
        # fallback can make a deployed camera appear healthy while it cannot
        # keep up with live frames, so fail before loading any model instead.
        configured_device = (device or os.getenv("FACERECO_DEVICE", "cuda")).strip().lower()
        if configured_device != "cuda":
            raise RuntimeError("FACERECO_DEVICE must be set to cuda")
        try:
            import onnxruntime as ort
            providers = ort.get_available_providers()
        except Exception as error:
            raise RuntimeError("CUDA-enabled ONNX Runtime is required") from error
        if "CUDAExecutionProvider" not in providers:
            raise RuntimeError(
                "CUDAExecutionProvider is unavailable; install the CUDA-enabled "
                "ONNX Runtime build for this host"
            )
        ctx_id = 0
        self.device = "cuda"

        # InsightFace 모델 로드
        try:
            # InsightFace 0.2.1 (구버전)과의 호환성 처리
            import insightface
            version = getattr(insightface, '__version__', '0.2.1')

            if production:
                # The exact directory was checked above. Selecting only this
                # bundle prevents InsightFace from falling back to another
                # model name and attempting a runtime download.
                self.app = create_analysis(self.model_name)
            elif version.startswith('0.2'):
                # 구버전: retinaface와 arcface 모델 조합 사용
                # 구버전에서는 빈 문자열 또는 특정 모델명 필요
                # name='antelopev2'를 시도하거나, 빈 문자열 사용
                try:
                    self.app = create_analysis('')
                except Exception:
                    # 빈 문자열도 안 되면 기본 모델 시도
                    try:
                        self.app = create_analysis('antelopev2')
                    except Exception:
                        # 마지막 시도: retinaface_r50_v1
                        self.app = create_analysis('retinaface_r50_v1')
            else:
                # 최신 버전: buffalo 모델 사용
                self.app = create_analysis(self.model_name)

            self.app.prepare(ctx_id=ctx_id, det_size=det_size)
            logger.info("face_model_ready")

            # 임베딩 크기 설정 (일반적으로 512차원)
            self.embedding_size = 512

        except Exception as exc:
            raise RuntimeError("InsightFace model could not be loaded") from exc

    def extract_embedding(
        self,
        image: np.ndarray,
        face_box: Optional[Tuple[int, int, int, int]] = None
    ) -> Optional[np.ndarray]:
        """
        이미지에서 얼굴 임베딩 추출

        Args:
            image (np.ndarray): 입력 이미지 (BGR 형식)
            face_box (Optional[Tuple[int, int, int, int]]): 얼굴 위치 (x, y, w, h),
                None이면 자동 감지

        Returns:
            Optional[np.ndarray]: 임베딩 벡터 (512차원) 또는 None (얼굴 미감지)
        """
        if image is None or image.size == 0:
            return None

        # RGB로 변환 (InsightFace는 RGB를 사용)
        if len(image.shape) == 3 and image.shape[2] == 3:
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        else:
            image_rgb = image

        # 얼굴 감지 및 분석
        faces = self.app.get(image_rgb)

        if len(faces) == 0:
            return None

        # face_box가 제공된 경우, 가장 가까운 얼굴 선택
        if face_box is not None:
            x, y, w, h = face_box
            box_center = np.array([x + w/2, y + h/2])

            min_dist = float('inf')
            selected_face = faces[0]

            for face in faces:
                face_bbox = face.bbox.astype(int)
                face_center = np.array([
                    (face_bbox[0] + face_bbox[2]) / 2,
                    (face_bbox[1] + face_bbox[3]) / 2
                ])
                dist = np.linalg.norm(box_center - face_center)

                if dist < min_dist:
                    min_dist = dist
                    selected_face = face

            return selected_face.embedding

        # face_box가 없으면 첫 번째 얼굴 사용
        return faces[0].embedding

    def extract_embeddings_batch(
        self,
        images: List[np.ndarray]
    ) -> List[Optional[np.ndarray]]:
        """
        여러 이미지에서 배치로 임베딩 추출

        Args:
            images (List[np.ndarray]): 이미지 리스트

        Returns:
            List[Optional[np.ndarray]]: 임베딩 벡터 리스트
        """
        embeddings = []
        for image in images:
            embedding = self.extract_embedding(image)
            embeddings.append(embedding)

        return embeddings

    @staticmethod
    def compute_similarity(
        embedding1: np.ndarray,
        embedding2: np.ndarray,
        metric: str = 'cosine'
    ) -> float:
        """
        두 임베딩 간 유사도 계산

        Args:
            embedding1 (np.ndarray): 첫 번째 임베딩
            embedding2 (np.ndarray): 두 번째 임베딩
            metric (str): 유사도 측정 방법 ('cosine', 'euclidean')

        Returns:
            float: 유사도 점수 (0.0-1.0, 높을수록 유사)
        """
        if embedding1 is None or embedding2 is None:
            return 0.0

        # 임베딩을 2D 배열로 변환 (sklearn 요구사항)
        emb1 = embedding1.reshape(1, -1)
        emb2 = embedding2.reshape(1, -1)

        if metric == 'cosine':
            # 코사인 유사도 계산
            similarity = cosine_similarity(emb1, emb2)[0][0]
            return float(similarity)

        elif metric == 'euclidean':
            # 유클리드 거리를 유사도로 변환
            distance = np.linalg.norm(embedding1 - embedding2)
            # 거리를 0-1 유사도로 변환 (임계값 1.4 사용)
            similarity = max(0.0, 1.0 - distance / 1.4)
            return float(similarity)

        else:
            raise ValueError(f"지원하지 않는 메트릭: {metric}")

    def detect_and_extract(
        self,
        image: np.ndarray
    ) -> List[dict]:
        """
        이미지에서 모든 얼굴 감지 및 임베딩 추출

        Args:
            image (np.ndarray): 입력 이미지

        Returns:
            List[dict]: 각 얼굴 정보 딕셔너리 리스트
                bbox: [x1, y1, x2, y2] 형식
                embedding: 512차원 임베딩 벡터
                age: 추정 나이 (int) 또는 None
                gender: 0=여성, 1=남성 또는 None
        """
        if image is None or image.size == 0:
            return []

        # RGB로 변환
        if len(image.shape) == 3 and image.shape[2] == 3:
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        else:
            image_rgb = image

        # 얼굴 감지 및 분석
        faces = self.app.get(image_rgb)

        results = []
        for face in faces:
            bbox = face.bbox.astype(int)
            embedding = face.embedding
            age = getattr(face, 'age', None)
            gender = getattr(face, 'gender', None)
            # Head Pose 추출 (yaw, pitch, roll)
            pose = getattr(face, 'pose', None)
            if pose is not None:
                pose = [float(v) for v in pose]

            results.append({
                'bbox': bbox,
                'embedding': embedding,
                'age': age,
                'gender': gender,
                'pose': pose,
            })

        return results

    def get_model_info(self) -> Dict:
        """
        모델 정보 반환

        Returns:
            Dict: 모델 이름, 디바이스, 임베딩 크기 등
        """
        return {
            'model_name': self.model_name,
            'device': self.device,
            'embedding_size': self.embedding_size,
            'det_size': self.det_size
        }


def demo_face_registration(camera_id: int = 0) -> None:
    """
    얼굴 등록 데모 함수

    사용자가 카메라 앞에서 이름을 입력하면 얼굴을 캡처하여 등록

    Args:
        camera_id (int): 카메라 ID
    """
    print("얼굴 등록 데모 시작...")
    print("스페이스바: 얼굴 캡처 | q: 종료")

    from camera.camera_handler import CameraHandler
    from models.face_database import FaceDatabase

    try:
        # 카메라 및 인식기 초기화
        camera = CameraHandler(camera_id)
        camera.open()

        recognizer = FaceRecognizer()
        database = FaceDatabase()

        frame_count = 0
        registered_count = 0

        while True:
            ret, frame = camera.read_frame()

            if not ret:
                break

            frame_count += 1
            display_frame = frame.copy()

            # 얼굴 감지 및 박스 표시
            results = recognizer.detect_and_extract(frame)

            for face_result in results:
                x1, y1, x2, y2 = face_result['bbox']
                cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

            # 안내 메시지 표시
            cv2.putText(
                display_frame,
                "Press SPACE to capture face",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 255),
                2
            )

            cv2.putText(
                display_frame,
                f"Registered: {registered_count}",
                (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 255),
                2
            )

            # 프레임 표시
            cv2.imshow('Face Registration', display_frame)

            key = cv2.waitKey(1) & 0xFF

            if key == ord(' '):  # 스페이스바 입력
                print("\n얼굴 캡처 중...")

                # 임베딩 추출
                embedding = recognizer.extract_embedding(frame)

                if embedding is not None:
                    # 이름 입력
                    name = input("이름을 입력하세요: ")

                    if name.strip():
                        # 데이터베이스에 등록
                        import datetime
                        face_id = f"person_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"

                        metadata = {
                            'name': name,
                            'registered_at': datetime.datetime.now().isoformat()
                        }

                        # 얼굴 이미지도 저장
                        success = database.register_face(face_id, embedding, metadata, frame)

                        if success:
                            registered_count += 1
                            print(f"✓ 등록 완료: {name} (ID: {face_id})")
                        else:
                            print(f"✗ 등록 실패")
                    else:
                        print("이름이 입력되지 않았습니다.")
                else:
                    print("✗ 얼굴을 감지할 수 없습니다. 다시 시도하세요.")

            elif key == ord('q'):
                break

        # 정리
        camera.release()
        cv2.destroyAllWindows()

        print(f"\n등록 완료:")
        print(f"- 총 프레임: {frame_count}")
        print(f"- 등록된 얼굴: {registered_count}")

    except Exception as e:
        print(f"데모 실행 중 오류: {str(e)}")
        import traceback
        traceback.print_exc()


def demo_face_recognition(camera_id: int = 0) -> None:
    """
    실시간 얼굴 인식 데모 함수

    카메라로 캡처한 얼굴을 데이터베이스와 비교하여 인식

    Args:
        camera_id (int): 카메라 ID
    """
    print("얼굴 인식 데모 시작...")
    print("q를 눌러 종료")

    from camera.camera_handler import CameraHandler
    from models.face_database import FaceDatabase

    try:
        # 카메라 및 인식기 초기화
        camera = CameraHandler(camera_id)
        camera.open()

        recognizer = FaceRecognizer()
        database = FaceDatabase()

        frame_count = 0
        recognition_stats = {"known": 0, "unknown": 0}

        while True:
            ret, frame = camera.read_frame()

            if not ret:
                break

            frame_count += 1
            display_frame = frame.copy()

            # 모든 얼굴 감지 및 임베딩 추출
            results = recognizer.detect_and_extract(frame)

            for face_result in results:
                bbox = face_result['bbox']
                embedding = face_result['embedding']
                age = face_result.get('age')
                gender = face_result.get('gender')
                x1, y1, x2, y2 = bbox

                # 나이/성별 문자열 생성
                ag_parts = []
                if gender is not None:
                    ag_parts.append("남성" if gender == 1 else "여성")
                if age is not None:
                    ag_parts.append(f"{age}세")
                age_gender_str = ", ".join(ag_parts)

                # 데이터베이스에서 매칭
                match = database.recognize_face(embedding)

                if match:
                    face_id, confidence = match
                    face_data = database.faces.get(face_id)
                    name = face_data['metadata'].get('name', 'Unknown') if face_data else 'Unknown'

                    recognition_stats["known"] += 1

                    # 녹색 박스 + 이름 + 신뢰도
                    color = (0, 255, 0)
                    label = f"{name} ({confidence:.2f})"
                else:
                    recognition_stats["unknown"] += 1

                    # 빨간색 박스 + Unknown
                    color = (0, 0, 255)
                    label = "Unknown"

                if age_gender_str:
                    label = f"{label} {age_gender_str}"

                # 박스 그리기
                cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, 2)

                # 레이블 배경 (Pillow 기반 한글 지원)
                font_size = 20
                text_w, text_h = get_text_size(label, font_size)

                cv2.rectangle(
                    display_frame,
                    (x1, y1 - text_h - 10),
                    (x1 + text_w + 4, y1),
                    color,
                    -1
                )

                # 레이블 텍스트 (한글 지원)
                put_korean_text(
                    display_frame,
                    label,
                    (x1 + 2, y1 - text_h - 6),
                    font_size=font_size,
                    color=(255, 255, 255),
                )

            # 통계 정보 표시
            cv2.putText(
                display_frame,
                f"Known: {recognition_stats['known']} | Unknown: {recognition_stats['unknown']}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 255),
                2
            )

            cv2.putText(
                display_frame,
                f"DB: {len(database.faces)} faces",
                (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 255),
                2
            )

            # 프레임 표시
            cv2.imshow('Face Recognition', display_frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        # 정리
        camera.release()
        cv2.destroyAllWindows()

        print(f"\n통계:")
        print(f"- 총 프레임: {frame_count}")
        print(f"- 인식된 얼굴 (Known): {recognition_stats['known']}")
        print(f"- 미등록 얼굴 (Unknown): {recognition_stats['unknown']}")
        print(f"- 데이터베이스 크기: {len(database.faces)} 명")

    except Exception as e:
        print(f"데모 실행 중 오류: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 간단한 테스트
    print("얼굴 인식 모듈 테스트")

    try:
        recognizer = FaceRecognizer()
        print(f"모델 정보: {recognizer.get_model_info()}")
    except Exception as e:
        print(f"오류: {str(e)}")
