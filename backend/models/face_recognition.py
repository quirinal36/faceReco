"""
얼굴 인식 모듈

InsightFace를 이용한 얼굴 임베딩 추출 및 인식
"""

import cv2
import numpy as np
from typing import Optional, Tuple, List, Dict
from sklearn.metrics.pairwise import cosine_similarity


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
        model_name: str = 'buffalo_l',
        device: str = 'auto',
        det_size: Tuple[int, int] = (640, 640)
    ):
        """
        얼굴 인식기 초기화

        Args:
            model_name (str): InsightFace 모델 이름 (buffalo_l, buffalo_m, buffalo_s)
            device (str): 실행 디바이스 ('auto', 'cuda', 'cpu')
            det_size (Tuple[int, int]): 얼굴 감지 입력 크기
        """
        self.model_name = model_name
        self.det_size = det_size

        # InsightFace import (지연 로딩)
        try:
            from insightface.app import FaceAnalysis
        except ImportError:
            raise RuntimeError(
                "InsightFace 패키지가 설치되어 있지 않습니다. "
                "'pip install insightface onnxruntime'을 실행하세요."
            )

        # 디바이스 설정
        if device == 'auto':
            # CUDA 사용 가능 여부 확인
            try:
                import onnxruntime as ort
                if 'CUDAExecutionProvider' in ort.get_available_providers():
                    ctx_id = 0  # GPU
                    self.device = 'cuda'
                else:
                    ctx_id = -1  # CPU
                    self.device = 'cpu'
            except:
                ctx_id = -1
                self.device = 'cpu'
        elif device == 'cuda':
            ctx_id = 0
            self.device = 'cuda'
        else:
            ctx_id = -1
            self.device = 'cpu'

        print(f"얼굴 인식 초기화 중... (모델: {model_name}, 디바이스: {self.device})")

        # InsightFace 모델 로드
        try:
            self.app = FaceAnalysis(name=model_name)
            self.app.prepare(ctx_id=ctx_id, det_size=det_size)
            print(f"얼굴 인식기 초기화 완료")

            # 임베딩 크기 설정 (buffalo_l은 512차원)
            self.embedding_size = 512

        except Exception as e:
            raise RuntimeError(f"InsightFace 모델 로드 실패: {str(e)}")

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
    ) -> List[Tuple[np.ndarray, np.ndarray]]:
        """
        이미지에서 모든 얼굴 감지 및 임베딩 추출

        Args:
            image (np.ndarray): 입력 이미지

        Returns:
            List[Tuple[np.ndarray, np.ndarray]]: (bbox, embedding) 리스트
                bbox: [x1, y1, x2, y2] 형식
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
            results.append((bbox, embedding))

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

            for bbox, _ in results:
                x1, y1, x2, y2 = bbox
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

            for bbox, embedding in results:
                x1, y1, x2, y2 = bbox

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

                # 박스 그리기
                cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, 2)

                # 레이블 배경
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 0.6
                font_thickness = 2
                text_size = cv2.getTextSize(label, font, font_scale, font_thickness)[0]

                cv2.rectangle(
                    display_frame,
                    (x1, y1 - text_size[1] - 10),
                    (x1 + text_size[0], y1),
                    color,
                    -1
                )

                # 레이블 텍스트
                cv2.putText(
                    display_frame,
                    label,
                    (x1, y1 - 5),
                    font,
                    font_scale,
                    (255, 255, 255),
                    font_thickness
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
