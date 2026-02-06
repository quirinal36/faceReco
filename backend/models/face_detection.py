"""
얼굴 감지 모듈

Haar Cascade를 이용한 실시간 얼굴 감지
"""

import cv2
import numpy as np
from typing import List, Tuple, Optional


class FaceDetector:
    """
    Haar Cascade를 이용한 얼굴 감지 클래스

    Attributes:
        face_cascade: OpenCV Haar Cascade 분류기
        scale_factor (float): 이미지 크기 조정 비율
        min_neighbors (int): 얼굴로 판단하기 위한 최소 이웃 개수
        min_size (Tuple[int, int]): 감지할 최소 얼굴 크기
    """

    def __init__(
        self,
        scale_factor: float = 1.1,
        min_neighbors: int = 5,
        min_size: Tuple[int, int] = (30, 30)
    ):
        """
        얼굴 감지기 초기화

        Args:
            scale_factor (float): 이미지 피라미드 스케일 팩터
            min_neighbors (int): 얼굴 검출을 위한 최소 이웃 수
            min_size (Tuple[int, int]): 감지할 최소 얼굴 크기
        """
        self.scale_factor = scale_factor
        self.min_neighbors = min_neighbors
        self.min_size = min_size

        # Haar Cascade 분류기 로드
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )

        if self.face_cascade.empty():
            raise RuntimeError("Haar Cascade 분류기를 로드할 수 없습니다.")

        print("얼굴 감지기 초기화 완료")

    def detect_faces(
        self,
        frame: np.ndarray,
        grayscale: bool = True
    ) -> List[Tuple[int, int, int, int]]:
        """
        프레임에서 얼굴 감지

        Args:
            frame (np.ndarray): 입력 이미지 프레임
            grayscale (bool): 그레이스케일 변환 여부

        Returns:
            List[Tuple[int, int, int, int]]: 감지된 얼굴 영역 리스트 [(x, y, w, h), ...]
        """
        if frame is None or frame.size == 0:
            return []

        # 그레이스케일 변환
        if grayscale and len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame

        # 얼굴 감지
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=self.scale_factor,
            minNeighbors=self.min_neighbors,
            minSize=self.min_size
        )

        return [tuple(face) for face in faces]

    def draw_faces(
        self,
        frame: np.ndarray,
        faces: List[Tuple[int, int, int, int]],
        color: Tuple[int, int, int] = (0, 255, 0),
        thickness: int = 2,
        show_label: bool = True
    ) -> np.ndarray:
        """
        프레임에 감지된 얼굴 영역 표시

        Args:
            frame (np.ndarray): 입력 이미지 프레임
            faces (List[Tuple[int, int, int, int]]): 얼굴 영역 리스트
            color (Tuple[int, int, int]): 바운딩 박스 색상 (BGR)
            thickness (int): 선 두께
            show_label (bool): 레이블 표시 여부

        Returns:
            np.ndarray: 얼굴 영역이 표시된 프레임
        """
        result_frame = frame.copy()

        for i, (x, y, w, h) in enumerate(faces):
            # 바운딩 박스 그리기
            cv2.rectangle(result_frame, (x, y), (x + w, y + h), color, thickness)

            if show_label:
                # 레이블 텍스트
                label = f"Face {i + 1}"

                # 텍스트 배경
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 0.6
                font_thickness = 2
                text_size = cv2.getTextSize(label, font, font_scale, font_thickness)[0]

                # 배경 사각형
                cv2.rectangle(
                    result_frame,
                    (x, y - text_size[1] - 10),
                    (x + text_size[0], y),
                    color,
                    -1
                )

                # 텍스트
                cv2.putText(
                    result_frame,
                    label,
                    (x, y - 5),
                    font,
                    font_scale,
                    (255, 255, 255),
                    font_thickness
                )

        return result_frame

    def get_face_count(self, faces: List[Tuple[int, int, int, int]]) -> int:
        """
        감지된 얼굴 개수 반환

        Args:
            faces (List[Tuple[int, int, int, int]]): 얼굴 영역 리스트

        Returns:
            int: 얼굴 개수
        """
        return len(faces)

    def extract_face_regions(
        self,
        frame: np.ndarray,
        faces: List[Tuple[int, int, int, int]],
        padding: int = 10
    ) -> List[np.ndarray]:
        """
        프레임에서 얼굴 영역 추출

        Args:
            frame (np.ndarray): 입력 이미지 프레임
            faces (List[Tuple[int, int, int, int]]): 얼굴 영역 리스트
            padding (int): 얼굴 영역 주변 패딩

        Returns:
            List[np.ndarray]: 추출된 얼굴 이미지 리스트
        """
        face_images = []
        h, w = frame.shape[:2]

        for (x, y, fw, fh) in faces:
            # 패딩 적용
            x1 = max(0, x - padding)
            y1 = max(0, y - padding)
            x2 = min(w, x + fw + padding)
            y2 = min(h, y + fh + padding)

            # 얼굴 영역 추출
            face_img = frame[y1:y2, x1:x2]
            face_images.append(face_img)

        return face_images


def demo_face_detection(camera_id: int = 0) -> None:
    """
    얼굴 감지 데모 함수

    Args:
        camera_id (int): 카메라 ID
    """
    print("얼굴 감지 데모 시작...")
    print("q를 눌러 종료")

    # 카메라 핸들러와 얼굴 감지기 초기화
    from camera.camera_handler import CameraHandler

    try:
        camera = CameraHandler(camera_id)
        camera.open()

        detector = FaceDetector()

        frame_count = 0
        total_faces = 0

        while True:
            ret, frame = camera.read_frame()

            if not ret:
                break

            frame_count += 1

            # 얼굴 감지
            faces = detector.detect_faces(frame)
            face_count = detector.get_face_count(faces)
            total_faces += face_count

            # 얼굴 영역 표시
            result_frame = detector.draw_faces(frame, faces)

            # 정보 표시
            info_text = f"Faces: {face_count} | Frame: {frame_count}"
            cv2.putText(
                result_frame,
                info_text,
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 255),
                2
            )

            # FPS 계산 및 표시
            if frame_count > 1:
                avg_faces = total_faces / frame_count
                cv2.putText(
                    result_frame,
                    f"Avg Faces: {avg_faces:.2f}",
                    (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 255),
                    2
                )

            # 프레임 표시
            cv2.imshow('Face Detection Demo', result_frame)

            # 'q' 키로 종료
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        # 정리
        camera.release()
        cv2.destroyAllWindows()

        print(f"\n데모 완료:")
        print(f"- 총 프레임: {frame_count}")
        print(f"- 총 감지된 얼굴: {total_faces}")
        print(f"- 평균 얼굴 수: {total_faces / frame_count if frame_count > 0 else 0:.2f}")

    except Exception as e:
        print(f"데모 실행 중 오류: {str(e)}")


if __name__ == "__main__":
    # 얼굴 감지 데모 실행
    demo_face_detection()
