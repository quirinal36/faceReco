"""
얼굴 감지 모듈 테스트
"""

import pytest
import sys
import os
import numpy as np
import cv2

# backend 모듈을 import하기 위한 경로 설정
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.models.face_detection import FaceDetector


class TestFaceDetector:
    """얼굴 감지기 테스트 클래스"""

    def test_face_detector_initialization(self):
        """얼굴 감지기 초기화 테스트"""
        detector = FaceDetector()
        assert detector.scale_factor == 1.1
        assert detector.min_neighbors == 5
        assert detector.min_size == (30, 30)
        assert detector.face_cascade is not None

    def test_face_detector_custom_parameters(self):
        """사용자 정의 파라미터 테스트"""
        detector = FaceDetector(
            scale_factor=1.2,
            min_neighbors=3,
            min_size=(40, 40)
        )
        assert detector.scale_factor == 1.2
        assert detector.min_neighbors == 3
        assert detector.min_size == (40, 40)

    def test_detect_faces_empty_image(self):
        """빈 이미지 얼굴 감지 테스트"""
        detector = FaceDetector()
        faces = detector.detect_faces(None)
        assert faces == []

    def test_detect_faces_blank_image(self):
        """빈 프레임 얼굴 감지 테스트"""
        detector = FaceDetector()
        # 검은색 이미지 생성
        blank_image = np.zeros((480, 640, 3), dtype=np.uint8)
        faces = detector.detect_faces(blank_image)
        # 검은색 이미지에서는 얼굴이 감지되지 않아야 함
        assert isinstance(faces, list)

    def test_get_face_count(self):
        """얼굴 개수 계산 테스트"""
        detector = FaceDetector()
        faces = [(10, 10, 50, 50), (100, 100, 50, 50)]
        count = detector.get_face_count(faces)
        assert count == 2

    def test_get_face_count_empty(self):
        """빈 얼굴 리스트 개수 테스트"""
        detector = FaceDetector()
        count = detector.get_face_count([])
        assert count == 0

    def test_draw_faces(self):
        """얼굴 영역 그리기 테스트"""
        detector = FaceDetector()
        # 테스트 이미지 생성
        image = np.zeros((480, 640, 3), dtype=np.uint8)
        faces = [(100, 100, 100, 100)]

        result = detector.draw_faces(image, faces)

        # 결과가 numpy array인지 확인
        assert isinstance(result, np.ndarray)
        # 원본 이미지와 크기가 같은지 확인
        assert result.shape == image.shape

    def test_draw_faces_no_label(self):
        """레이블 없이 얼굴 영역 그리기 테스트"""
        detector = FaceDetector()
        image = np.zeros((480, 640, 3), dtype=np.uint8)
        faces = [(100, 100, 100, 100)]

        result = detector.draw_faces(image, faces, show_label=False)

        assert isinstance(result, np.ndarray)
        assert result.shape == image.shape

    def test_extract_face_regions(self):
        """얼굴 영역 추출 테스트"""
        detector = FaceDetector()
        # 테스트 이미지 생성 (640x480)
        image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        faces = [(100, 100, 100, 100)]

        face_images = detector.extract_face_regions(image, faces, padding=10)

        assert len(face_images) == 1
        assert isinstance(face_images[0], np.ndarray)
        # 패딩을 포함한 크기 확인 (100 + 10*2 = 120)
        assert face_images[0].shape[0] == 120
        assert face_images[0].shape[1] == 120

    def test_extract_face_regions_multiple(self):
        """여러 얼굴 영역 추출 테스트"""
        detector = FaceDetector()
        image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        faces = [(50, 50, 80, 80), (200, 200, 100, 100)]

        face_images = detector.extract_face_regions(image, faces)

        assert len(face_images) == 2

    def test_extract_face_regions_edge_case(self):
        """경계 케이스 얼굴 영역 추출 테스트"""
        detector = FaceDetector()
        image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        # 이미지 경계 근처의 얼굴
        faces = [(0, 0, 50, 50)]

        face_images = detector.extract_face_regions(image, faces, padding=10)

        assert len(face_images) == 1
        # 패딩이 이미지 경계를 넘지 않아야 함
        assert face_images[0].shape[0] <= 70  # 50 + 10*2
        assert face_images[0].shape[1] <= 70


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
