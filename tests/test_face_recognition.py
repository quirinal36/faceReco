"""
얼굴 인식 모듈 테스트
"""

import pytest
import numpy as np
import tempfile
import shutil
import os
from pathlib import Path


class TestFaceRecognizer:
    """얼굴 인식기 테스트"""

    @pytest.fixture(autouse=True)
    def skip_if_no_insightface(self):
        """InsightFace가 설치되지 않은 경우 테스트 건너뛰기"""
        try:
            import insightface
        except ImportError:
            pytest.skip("InsightFace가 설치되지 않았습니다")

    def test_initialization(self):
        """얼굴 인식기 초기화 테스트"""
        from backend.models.face_recognition import FaceRecognizer

        recognizer = FaceRecognizer(device='cpu')
        assert recognizer is not None
        assert recognizer.device == 'cpu'
        assert recognizer.model_name == 'buffalo_l'
        assert recognizer.embedding_size == 512

    def test_get_model_info(self):
        """모델 정보 조회 테스트"""
        from backend.models.face_recognition import FaceRecognizer

        recognizer = FaceRecognizer(device='cpu')
        info = recognizer.get_model_info()

        assert 'model_name' in info
        assert 'device' in info
        assert 'embedding_size' in info
        assert info['embedding_size'] == 512

    def test_compute_similarity_same_embedding(self):
        """동일한 임베딩 유사도 테스트"""
        from backend.models.face_recognition import FaceRecognizer

        # 임의의 임베딩 생성
        embedding = np.random.randn(512)

        # 동일한 임베딩의 유사도는 1.0이어야 함
        similarity = FaceRecognizer.compute_similarity(embedding, embedding)
        assert abs(similarity - 1.0) < 0.01

    def test_compute_similarity_different_embeddings(self):
        """다른 임베딩 유사도 테스트"""
        from backend.models.face_recognition import FaceRecognizer

        # 두 개의 다른 임베딩
        embedding1 = np.random.randn(512)
        embedding2 = np.random.randn(512)

        # 다른 임베딩의 유사도는 1.0보다 작아야 함
        similarity = FaceRecognizer.compute_similarity(embedding1, embedding2)
        assert 0.0 <= similarity <= 1.0
        assert similarity < 0.99

    def test_compute_similarity_euclidean(self):
        """유클리드 거리 기반 유사도 테스트"""
        from backend.models.face_recognition import FaceRecognizer

        embedding = np.random.randn(512)

        # 유클리드 메트릭으로 동일한 임베딩 비교
        similarity = FaceRecognizer.compute_similarity(
            embedding, embedding, metric='euclidean'
        )
        assert abs(similarity - 1.0) < 0.01


class TestFaceDatabase:
    """얼굴 데이터베이스 테스트"""

    @pytest.fixture
    def temp_db_dir(self):
        """임시 데이터베이스 디렉토리 생성"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def face_database(self, temp_db_dir):
        """임시 얼굴 데이터베이스 생성"""
        from backend.models.face_database import FaceDatabase

        db_path = os.path.join(temp_db_dir, 'test_database.json')
        db = FaceDatabase(db_path=db_path)
        return db

    def test_database_creation(self, face_database):
        """데이터베이스 생성 테스트"""
        assert face_database is not None
        assert len(face_database) == 0
        assert face_database.threshold == 0.5

    def test_register_face(self, face_database):
        """얼굴 등록 테스트"""
        # 임의의 임베딩 생성
        embedding = np.random.randn(512)

        metadata = {
            'name': '테스트',
            'registered_at': '2026-02-06T15:00:00'
        }

        # 얼굴 등록
        success = face_database.register_face('test_001', embedding, metadata)

        assert success is True
        assert len(face_database) == 1
        assert 'test_001' in face_database.faces

    def test_find_match(self, face_database):
        """얼굴 매칭 테스트"""
        # 임베딩 등록
        embedding1 = np.random.randn(512)
        face_database.register_face('person_001', embedding1, {'name': 'A'})

        # 동일한 임베딩으로 검색
        matches = face_database.find_match(embedding1, top_k=1)

        assert len(matches) == 1
        assert matches[0][0] == 'person_001'
        assert matches[0][1] > 0.99  # 동일한 임베딩이므로 매우 높은 유사도

    def test_recognize_face(self, face_database):
        """얼굴 인식 테스트"""
        # 임베딩 등록
        embedding = np.random.randn(512)
        face_database.register_face('person_001', embedding, {'name': 'B'})

        # 동일한 임베딩으로 인식
        result = face_database.recognize_face(embedding)

        assert result is not None
        assert result[0] == 'person_001'
        assert result[1] > 0.5  # 임계값 이상

    def test_recognize_face_no_match(self, face_database):
        """매칭되지 않는 얼굴 인식 테스트"""
        # 임베딩 등록
        embedding1 = np.random.randn(512)
        face_database.register_face('person_001', embedding1, {'name': 'C'})

        # 완전히 다른 임베딩으로 검색
        embedding2 = np.random.randn(512)
        result = face_database.recognize_face(embedding2)

        # 임계값 미만이면 None 반환
        # (랜덤 임베딩이므로 매칭 안 될 가능성 높음)
        if result is not None:
            assert result[1] < 0.9  # 완전히 다른 임베딩이므로 낮은 유사도

    def test_remove_face(self, face_database):
        """얼굴 삭제 테스트"""
        # 임베딩 등록
        embedding = np.random.randn(512)
        face_database.register_face('person_001', embedding, {'name': 'D'})

        assert len(face_database) == 1

        # 얼굴 삭제
        success = face_database.remove_face('person_001')

        assert success is True
        assert len(face_database) == 0

    def test_update_metadata(self, face_database):
        """메타데이터 업데이트 테스트"""
        # 임베딩 등록
        embedding = np.random.randn(512)
        face_database.register_face('person_001', embedding, {'name': 'E'})

        # 메타데이터 업데이트
        new_metadata = {'department': '개발팀'}
        success = face_database.update_metadata('person_001', new_metadata)

        assert success is True
        assert 'department' in face_database.faces['person_001']['metadata']

    def test_save_and_load(self, face_database, temp_db_dir):
        """데이터베이스 저장 및 로드 테스트"""
        from backend.models.face_database import FaceDatabase

        # 임베딩 등록
        embedding = np.random.randn(512)
        face_database.register_face('person_001', embedding, {'name': 'F'})

        # 저장
        success = face_database.save()
        assert success is True

        # 새 데이터베이스 인스턴스로 로드
        db_path = os.path.join(temp_db_dir, 'test_database.json')
        new_db = FaceDatabase(db_path=db_path)

        assert len(new_db) == 1
        assert 'person_001' in new_db.faces

    def test_context_manager(self, temp_db_dir):
        """Context manager 테스트"""
        from backend.models.face_database import FaceDatabase

        db_path = os.path.join(temp_db_dir, 'test_database.json')

        # Context manager로 사용
        with FaceDatabase(db_path=db_path) as db:
            embedding = np.random.randn(512)
            db.register_face('person_001', embedding, {'name': 'G'})

        # 자동 저장 확인
        new_db = FaceDatabase(db_path=db_path)
        assert len(new_db) == 1

    def test_get_all_faces(self, face_database):
        """모든 얼굴 조회 테스트"""
        # 여러 얼굴 등록
        for i in range(3):
            embedding = np.random.randn(512)
            face_database.register_face(f'person_{i:03d}', embedding, {'name': f'Person{i}'})

        # 모든 얼굴 조회
        all_faces = face_database.get_all_faces()

        assert len(all_faces) == 3
        assert all(isinstance(face, dict) for face in all_faces)

    def test_get_statistics(self, face_database):
        """통계 조회 테스트"""
        # 얼굴 등록
        embedding = np.random.randn(512)
        face_database.register_face('person_001', embedding, {'name': 'H'})

        # 통계 조회
        stats = face_database.get_statistics()

        assert stats['total_faces'] == 1
        assert 'threshold' in stats
        assert 'model_name' in stats


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
