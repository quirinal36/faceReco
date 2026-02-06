"""
카메라 핸들러 모듈

OpenCV를 이용한 카메라 스트림 처리
"""

import cv2
import numpy as np
from typing import Optional, Tuple


class CameraHandler:
    """
    카메라 스트림을 처리하는 핸들러 클래스

    Attributes:
        camera_id (int): 카메라 장치 ID (기본값: 0)
        capture (cv2.VideoCapture): OpenCV VideoCapture 객체
        is_opened (bool): 카메라 연결 상태
    """

    def __init__(self, camera_id: int = 0):
        """
        카메라 핸들러 초기화

        Args:
            camera_id (int): 카메라 장치 ID (기본값: 0 - 기본 웹캠)
        """
        self.camera_id = camera_id
        self.capture: Optional[cv2.VideoCapture] = None
        self.is_opened = False

    def open(self) -> bool:
        """
        카메라 연결 시작

        Returns:
            bool: 연결 성공 여부

        Raises:
            RuntimeError: 카메라 연결 실패 시
        """
        try:
            self.capture = cv2.VideoCapture(self.camera_id)

            if not self.capture.isOpened():
                raise RuntimeError(f"카메라 ID {self.camera_id}를 열 수 없습니다.")

            # 카메라 설정
            self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.capture.set(cv2.CAP_PROP_FPS, 30)

            self.is_opened = True
            print(f"카메라 ID {self.camera_id} 연결 성공")
            return True

        except Exception as e:
            self.is_opened = False
            raise RuntimeError(f"카메라 연결 중 오류 발생: {str(e)}")

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        카메라에서 프레임 읽기

        Returns:
            Tuple[bool, Optional[np.ndarray]]: (성공 여부, 프레임 이미지)
        """
        if not self.is_opened or self.capture is None:
            return False, None

        ret, frame = self.capture.read()

        if not ret:
            print("프레임을 읽을 수 없습니다.")
            return False, None

        return True, frame

    def release(self) -> None:
        """카메라 리소스 해제"""
        if self.capture is not None:
            self.capture.release()
            self.is_opened = False
            print("카메라 연결 해제")

    def get_frame_size(self) -> Tuple[int, int]:
        """
        현재 프레임 크기 반환

        Returns:
            Tuple[int, int]: (width, height)
        """
        if not self.is_opened or self.capture is None:
            return (0, 0)

        width = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))

        return (width, height)

    def get_fps(self) -> float:
        """
        현재 FPS 반환

        Returns:
            float: FPS 값
        """
        if not self.is_opened or self.capture is None:
            return 0.0

        return self.capture.get(cv2.CAP_PROP_FPS)

    def __enter__(self):
        """Context manager 진입"""
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager 종료"""
        self.release()

    def __del__(self):
        """소멸자 - 리소스 정리"""
        self.release()


def test_camera(camera_id: int = 0, duration: int = 10) -> None:
    """
    카메라 테스트 함수

    Args:
        camera_id (int): 테스트할 카메라 ID
        duration (int): 테스트 지속 시간 (초)
    """
    print(f"카메라 테스트 시작 (ID: {camera_id}, 지속시간: {duration}초)")

    try:
        with CameraHandler(camera_id) as camera:
            width, height = camera.get_frame_size()
            fps = camera.get_fps()

            print(f"카메라 정보 - 해상도: {width}x{height}, FPS: {fps}")
            print("프레임 캡처 중... (q를 눌러 종료)")

            frame_count = 0

            while True:
                ret, frame = camera.read_frame()

                if not ret:
                    break

                frame_count += 1

                # 프레임 정보 표시
                cv2.putText(
                    frame,
                    f"Frame: {frame_count}",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 255, 0),
                    2
                )

                # 프레임 표시
                cv2.imshow('Camera Test', frame)

                # 'q' 키를 누르면 종료
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

            cv2.destroyAllWindows()
            print(f"테스트 완료 - 총 {frame_count} 프레임 캡처")

    except Exception as e:
        print(f"카메라 테스트 중 오류: {str(e)}")


if __name__ == "__main__":
    # 카메라 테스트 실행
    test_camera()
