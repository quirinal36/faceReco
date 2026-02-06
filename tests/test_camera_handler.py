"""
카메라 핸들러 테스트
"""

import pytest
import sys
import os

# backend 모듈을 import하기 위한 경로 설정
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.camera.camera_handler import CameraHandler


class TestCameraHandler:
    """카메라 핸들러 테스트 클래스"""

    def test_camera_handler_initialization(self):
        """카메라 핸들러 초기화 테스트"""
        camera = CameraHandler(camera_id=0)
        assert camera.camera_id == 0
        assert camera.capture is None
        assert camera.is_opened is False

    def test_camera_handler_custom_id(self):
        """사용자 정의 카메라 ID 테스트"""
        camera = CameraHandler(camera_id=1)
        assert camera.camera_id == 1

    def test_get_frame_size_before_open(self):
        """카메라 오픈 전 프레임 크기 조회 테스트"""
        camera = CameraHandler()
        width, height = camera.get_frame_size()
        assert width == 0
        assert height == 0

    def test_get_fps_before_open(self):
        """카메라 오픈 전 FPS 조회 테스트"""
        camera = CameraHandler()
        fps = camera.get_fps()
        assert fps == 0.0

    def test_read_frame_before_open(self):
        """카메라 오픈 전 프레임 읽기 테스트"""
        camera = CameraHandler()
        ret, frame = camera.read_frame()
        assert ret is False
        assert frame is None

    def test_release_without_open(self):
        """카메라 오픈 없이 release 호출 테스트"""
        camera = CameraHandler()
        camera.release()  # 에러가 발생하지 않아야 함
        assert camera.is_opened is False


# 실제 카메라가 필요한 테스트 (선택적 실행)
@pytest.mark.skipif(
    not os.path.exists('/dev/video0') and sys.platform == 'linux',
    reason="카메라 장치가 없습니다"
)
class TestCameraHandlerWithDevice:
    """실제 카메라 장치가 필요한 테스트"""

    def test_camera_open_and_close(self):
        """카메라 열기 및 닫기 테스트"""
        camera = CameraHandler()
        try:
            result = camera.open()
            assert result is True
            assert camera.is_opened is True
        except RuntimeError:
            pytest.skip("카메라를 열 수 없습니다")
        finally:
            camera.release()
            assert camera.is_opened is False

    def test_context_manager(self):
        """Context manager 테스트"""
        try:
            with CameraHandler() as camera:
                assert camera.is_opened is True
                width, height = camera.get_frame_size()
                assert width > 0
                assert height > 0
        except RuntimeError:
            pytest.skip("카메라를 열 수 없습니다")
