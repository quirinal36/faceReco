"""
얼굴 데이터베이스 모듈

얼굴 임베딩 저장, 검색 및 관리
"""

import os
import json
import numpy as np
import cv2
from typing import Optional, List, Tuple, Dict
from datetime import datetime
from sklearn.metrics.pairwise import cosine_similarity


class FaceDatabase:
    """
    얼굴 데이터베이스 관리 클래스

    Attributes:
        db_path (str): 데이터베이스 JSON 파일 경로
        data_dir (str): 데이터 디렉토리 경로
        embeddings_dir (str): 임베딩 파일 디렉토리
        faces_dir (str): 얼굴 이미지 디렉토리
        faces (Dict): 얼굴 데이터 딕셔너리
        threshold (float): 매칭 임계값
    """

    def __init__(
        self,
        db_path: str = "data/face_database.json",
        threshold: float = 0.5
    ):
        """
        얼굴 데이터베이스 초기화

        Args:
            db_path (str): 데이터베이스 파일 경로 (상대 경로)
            threshold (float): 얼굴 매칭 임계값 (0.0-1.0)
        """
        # 경로 설정 (backend 디렉토리 기준)
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.db_path = os.path.join(backend_dir, db_path)
        self.data_dir = os.path.dirname(self.db_path)
        self.embeddings_dir = os.path.join(self.data_dir, 'embeddings')
        self.faces_dir = os.path.join(self.data_dir, 'faces')

        self.threshold = threshold
        self.faces = {}
        self.config = {
            'threshold': threshold,
            'model_name': 'buffalo_l',
            'embedding_size': 512
        }

        # 디렉토리 생성
        self._create_directories()

        # 데이터베이스 로드
        self.load()

    def _create_directories(self) -> None:
        """필요한 디렉토리 생성"""
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.embeddings_dir, exist_ok=True)
        os.makedirs(self.faces_dir, exist_ok=True)

    def register_face(
        self,
        face_id: str,
        embedding: np.ndarray,
        metadata: Optional[Dict] = None,
        face_image: Optional[np.ndarray] = None
    ) -> bool:
        """
        새로운 얼굴 등록

        Args:
            face_id (str): 고유 얼굴 ID
            embedding (np.ndarray): 얼굴 임베딩 벡터
            metadata (Optional[Dict]): 추가 정보 (이름, 등록일 등)
            face_image (Optional[np.ndarray]): 얼굴 이미지

        Returns:
            bool: 등록 성공 여부
        """
        try:
            # 임베딩 저장
            embedding_path = os.path.join(self.embeddings_dir, f"{face_id}.npy")
            np.save(embedding_path, embedding)

            # 얼굴 이미지 저장 (선택사항)
            image_path = None
            if face_image is not None:
                image_path = os.path.join(self.faces_dir, f"{face_id}.jpg")
                cv2.imwrite(image_path, face_image)

            # 메타데이터 구성
            if metadata is None:
                metadata = {}

            face_data = {
                'face_id': face_id,
                'name': metadata.get('name', face_id),
                'embedding_path': f"embeddings/{face_id}.npy",
                'image_path': f"faces/{face_id}.jpg" if image_path else None,
                'registered_at': metadata.get('registered_at', datetime.now().isoformat()),
                'last_seen': None,
                'recognition_count': 0,
                'metadata': metadata
            }

            # 데이터베이스에 추가
            self.faces[face_id] = face_data

            # 자동 저장
            self.save()

            return True

        except Exception as e:
            print(f"얼굴 등록 실패: {str(e)}")
            return False

    def find_match(
        self,
        embedding: np.ndarray,
        top_k: int = 1
    ) -> List[Tuple[str, float]]:
        """
        임베딩과 가장 유사한 얼굴 검색

        Args:
            embedding (np.ndarray): 쿼리 임베딩
            top_k (int): 반환할 최대 결과 수

        Returns:
            List[Tuple[str, float]]: (face_id, similarity) 리스트 (내림차순)
        """
        if len(self.faces) == 0:
            return []

        similarities = []

        for face_id, face_data in self.faces.items():
            # 임베딩 로드
            embedding_path = os.path.join(
                self.data_dir,
                face_data['embedding_path']
            )

            if not os.path.exists(embedding_path):
                continue

            stored_embedding = np.load(embedding_path)

            # 유사도 계산
            emb1 = embedding.reshape(1, -1)
            emb2 = stored_embedding.reshape(1, -1)
            similarity = cosine_similarity(emb1, emb2)[0][0]

            similarities.append((face_id, float(similarity)))

        # 유사도 기준 내림차순 정렬
        similarities.sort(key=lambda x: x[1], reverse=True)

        # top_k 개만 반환
        return similarities[:top_k]

    def recognize_face(
        self,
        embedding: np.ndarray
    ) -> Optional[Tuple[str, float]]:
        """
        얼굴 인식 수행

        Args:
            embedding (np.ndarray): 쿼리 임베딩

        Returns:
            Optional[Tuple[str, float]]: (face_id, confidence) 또는 None (매칭 실패)
        """
        matches = self.find_match(embedding, top_k=1)

        if len(matches) == 0:
            return None

        face_id, similarity = matches[0]

        # 임계값 확인
        if similarity >= self.threshold:
            # 통계 업데이트
            self._update_recognition_stats(face_id)
            return (face_id, similarity)

        return None

    def _update_recognition_stats(self, face_id: str) -> None:
        """인식 통계 업데이트"""
        if face_id in self.faces:
            self.faces[face_id]['last_seen'] = datetime.now().isoformat()
            self.faces[face_id]['recognition_count'] += 1

    def remove_face(self, face_id: str) -> bool:
        """
        얼굴 삭제

        Args:
            face_id (str): 삭제할 얼굴 ID

        Returns:
            bool: 삭제 성공 여부
        """
        if face_id not in self.faces:
            return False

        try:
            face_data = self.faces[face_id]

            # 임베딩 파일 삭제
            embedding_path = os.path.join(self.data_dir, face_data['embedding_path'])
            if os.path.exists(embedding_path):
                os.remove(embedding_path)

            # 이미지 파일 삭제
            if face_data.get('image_path'):
                image_path = os.path.join(self.data_dir, face_data['image_path'])
                if os.path.exists(image_path):
                    os.remove(image_path)

            # 데이터베이스에서 제거
            del self.faces[face_id]

            # 저장
            self.save()

            return True

        except Exception as e:
            print(f"얼굴 삭제 실패: {str(e)}")
            return False

    def update_metadata(self, face_id: str, metadata: Dict) -> bool:
        """
        메타데이터 업데이트

        Args:
            face_id (str): 얼굴 ID
            metadata (Dict): 새 메타데이터

        Returns:
            bool: 업데이트 성공 여부
        """
        if face_id not in self.faces:
            return False

        self.faces[face_id]['metadata'].update(metadata)
        self.save()
        return True

    def get_all_faces(self) -> List[Dict]:
        """
        등록된 모든 얼굴 정보 반환

        Returns:
            List[Dict]: 얼굴 정보 리스트
        """
        return list(self.faces.values())

    def save(self) -> bool:
        """
        데이터베이스 저장

        Returns:
            bool: 저장 성공 여부
        """
        try:
            db_data = {
                'version': '1.0',
                'created_at': datetime.now().isoformat(),
                'last_updated': datetime.now().isoformat(),
                'faces': self.faces,
                'config': self.config
            }

            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(db_data, f, indent=2, ensure_ascii=False)

            return True

        except Exception as e:
            print(f"데이터베이스 저장 실패: {str(e)}")
            return False

    def load(self) -> bool:
        """
        데이터베이스 로드

        Returns:
            bool: 로드 성공 여부
        """
        if not os.path.exists(self.db_path):
            print(f"데이터베이스 파일이 없습니다. 새로 생성합니다: {self.db_path}")
            return False

        try:
            with open(self.db_path, 'r', encoding='utf-8') as f:
                db_data = json.load(f)

            self.faces = db_data.get('faces', {})
            self.config = db_data.get('config', self.config)

            # config에서 threshold 로드
            if 'threshold' in self.config:
                self.threshold = self.config['threshold']

            print(f"데이터베이스 로드 완료: {len(self.faces)}명의 얼굴 데이터")
            return True

        except Exception as e:
            print(f"데이터베이스 로드 실패: {str(e)}")
            return False

    def get_statistics(self) -> Dict:
        """
        데이터베이스 통계 반환

        Returns:
            Dict: 통계 정보
        """
        total_recognitions = sum(
            face['recognition_count'] for face in self.faces.values()
        )

        return {
            'total_faces': len(self.faces),
            'total_recognitions': total_recognitions,
            'threshold': self.threshold,
            'model_name': self.config.get('model_name', 'buffalo_l'),
            'db_path': self.db_path
        }

    def __enter__(self):
        """Context manager 진입"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager 종료 (자동 저장)"""
        self.save()

    def __len__(self) -> int:
        """데이터베이스 크기 반환"""
        return len(self.faces)

    def __repr__(self) -> str:
        """문자열 표현"""
        return f"FaceDatabase(faces={len(self.faces)}, threshold={self.threshold})"


if __name__ == "__main__":
    # 간단한 테스트
    print("얼굴 데이터베이스 모듈 테스트")

    db = FaceDatabase()
    print(f"데이터베이스: {db}")
    print(f"통계: {db.get_statistics()}")
