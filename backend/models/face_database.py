"""
얼굴 데이터베이스 모듈

얼굴 임베딩 저장, 검색 및 관리
"""

import os
import json
import copy
import logging
import re
import tempfile
import numpy as np
import cv2
from pathlib import Path
from typing import Optional, List, Tuple, Dict
from datetime import datetime
from sklearn.metrics.pairwise import cosine_similarity

try:
    from utils.private_storage import ensure_private_directory, ensure_private_file
except ModuleNotFoundError:  # Imported as backend.models.face_database in tests.
    from backend.utils.private_storage import ensure_private_directory, ensure_private_file


logger = logging.getLogger(__name__)
SAFE_FACE_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
THUMBNAIL_MAX_SIZE = 256


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
        self._load_failed = False
        self.config = {
            'threshold': threshold,
            'model_name': 'default',
            'embedding_size': 512
        }

        # 디렉토리 생성
        self._create_directories()

        # 데이터베이스 로드
        self.load()

    def _create_directories(self) -> None:
        """필요한 디렉토리 생성"""
        ensure_private_directory(self.data_dir)
        ensure_private_directory(self.embeddings_dir)
        ensure_private_directory(self.faces_dir)

        for directory, suffixes in (
            (Path(self.embeddings_dir), {".npy"}),
            (Path(self.faces_dir), {".jpg", ".jpeg"}),
        ):
            for path in directory.iterdir():
                if path.is_symlink():
                    raise RuntimeError(
                        "Private biometric storage cannot contain symbolic links"
                    )
                if path.is_file() and path.suffix.lower() in suffixes:
                    ensure_private_file(path)

        database_path = Path(self.db_path)
        if database_path.is_symlink():
            raise RuntimeError("Face database cannot be a symbolic link")
        if database_path.exists():
            ensure_private_file(database_path)

    @staticmethod
    def _validate_face_id(face_id: str) -> None:
        if not SAFE_FACE_ID.fullmatch(face_id):
            raise ValueError("Invalid face identifier")

    @staticmethod
    def _bounded_thumbnail(face_image: np.ndarray) -> np.ndarray:
        """Cap retained images even when non-API callers provide a full frame."""
        if face_image is None or face_image.size == 0:
            raise ValueError("Invalid thumbnail")
        height, width = face_image.shape[:2]
        scale = min(THUMBNAIL_MAX_SIZE / width, THUMBNAIL_MAX_SIZE / height, 1.0)
        if scale >= 1.0:
            return face_image
        return cv2.resize(
            face_image,
            (max(1, round(width * scale)), max(1, round(height * scale))),
            interpolation=cv2.INTER_AREA,
        )

    @staticmethod
    def _exclusive_open_flags() -> int:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        return flags

    def _write_embedding_exclusive(
        self, path: str | os.PathLike[str], embedding: np.ndarray
    ) -> None:
        """Create one embedding without following or replacing an old path."""
        file_descriptor = os.open(path, self._exclusive_open_flags(), 0o600)
        try:
            with os.fdopen(file_descriptor, "wb") as output:
                np.save(output, np.asarray(embedding), allow_pickle=False)
                output.flush()
                os.fsync(output.fileno())
            ensure_private_file(path)
        except Exception:
            try:
                candidate = Path(path)
                if candidate.is_file() and not candidate.is_symlink():
                    candidate.unlink()
            except OSError:
                logger.error("partial_embedding_cleanup_failed")
            raise

    def _write_thumbnail_exclusive(
        self, path: str | os.PathLike[str], face_image: np.ndarray
    ) -> None:
        """Encode and exclusively create one bounded JPEG thumbnail."""
        encoded, buffer = cv2.imencode(
            ".jpg",
            self._bounded_thumbnail(face_image),
            [int(cv2.IMWRITE_JPEG_QUALITY), 80],
        )
        if not encoded:
            raise RuntimeError("Thumbnail encoding failed")

        file_descriptor = os.open(path, self._exclusive_open_flags(), 0o600)
        try:
            with os.fdopen(file_descriptor, "wb") as output:
                output.write(buffer.tobytes())
                output.flush()
                os.fsync(output.fileno())
            ensure_private_file(path)
        except Exception:
            try:
                candidate = Path(path)
                if candidate.is_file() and not candidate.is_symlink():
                    candidate.unlink()
            except OSError:
                logger.error("partial_thumbnail_cleanup_failed")
            raise

    def _resolve_stored_path(
        self,
        relative_path: str,
        root: str,
        suffixes: set[str],
    ) -> Optional[Path]:
        """Resolve an existing store path and reject traversal or symlinks."""
        if not isinstance(relative_path, str):
            return None
        candidate = Path(self.data_dir, relative_path)
        if candidate.is_symlink() or candidate.suffix.lower() not in suffixes:
            return None
        try:
            resolved = candidate.resolve(strict=True)
            resolved.relative_to(Path(root).resolve(strict=True))
        except (FileNotFoundError, OSError, RuntimeError, ValueError):
            return None
        return resolved if resolved.is_file() else None

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
        created_paths: List[str] = []
        try:
            self._validate_face_id(face_id)
            if self._load_failed:
                raise RuntimeError("Face store is unavailable")
            if face_id in self.faces:
                raise ValueError("Face identifier already exists")

            # 임베딩 저장
            embedding_path = os.path.join(self.embeddings_dir, f"{face_id}.npy")
            self._write_embedding_exclusive(embedding_path, embedding)
            created_paths.append(embedding_path)

            # 얼굴 썸네일 저장 (선택사항). API 계층은 얼굴 bbox로 먼저 자릅니다.
            image_path = None
            if face_image is not None:
                image_path = os.path.join(self.faces_dir, f"{face_id}.jpg")
                self._write_thumbnail_exclusive(image_path, face_image)
                created_paths.append(image_path)

            # 메타데이터 구성
            if metadata is None:
                metadata = {}

            face_data = {
                'face_id': face_id,
                'name': metadata.get('name', face_id),
                'embedding_path': f"embeddings/{face_id}.npy",
                'embedding_paths': [f"embeddings/{face_id}.npy"],  # 다중 임베딩 지원
                'image_path': f"faces/{face_id}.jpg" if image_path else None,
                'image_paths': [f"faces/{face_id}.jpg"] if image_path else [],  # 다중 이미지 지원
                'registered_at': metadata.get('registered_at', datetime.now().isoformat()),
                'last_seen': None,
                'recognition_count': 0,
                'sample_count': 1,  # 샘플 개수
                'metadata': metadata
            }

            # 데이터베이스에 추가
            self.faces[face_id] = face_data

            # 자동 저장
            if not self.save():
                raise RuntimeError("Face store write failed")

            return True

        except Exception:
            self.faces.pop(face_id, None)
            for path in created_paths:
                try:
                    if os.path.isfile(path) and not os.path.islink(path):
                        os.remove(path)
                except OSError:
                    logger.error("biometric_registration_rollback_failed")
            logger.error("biometric_registration_failed")
            return False

    def add_face_sample(
        self,
        face_id: str,
        embedding: np.ndarray,
        face_image: Optional[np.ndarray] = None
    ) -> bool:
        """
        기존 얼굴에 추가 샘플 등록 (같은 사람의 다른 사진)

        Args:
            face_id (str): 기존 얼굴 ID
            embedding (np.ndarray): 새로운 얼굴 임베딩 벡터
            face_image (Optional[np.ndarray]): 새로운 얼굴 이미지

        Returns:
            bool: 추가 성공 여부
        """
        if face_id not in self.faces:
            return False

        embedding_path = None
        thumbnail_path = None
        original_face_data = copy.deepcopy(self.faces.get(face_id))
        try:
            self._validate_face_id(face_id)
            if self._load_failed:
                raise RuntimeError("Face store is unavailable")
            face_data = self.faces[face_id]

            # 샘플 인덱스 계산
            sample_idx = face_data.get('sample_count', 1)

            # 임베딩 저장
            embedding_path = os.path.join(self.embeddings_dir, f"{face_id}_{sample_idx}.npy")
            self._write_embedding_exclusive(embedding_path, embedding)

            # 임베딩 경로 추가
            if 'embedding_paths' not in face_data:
                # 기존 데이터 마이그레이션
                face_data['embedding_paths'] = [face_data.get('embedding_path', f"embeddings/{face_id}.npy")]

            face_data['embedding_paths'].append(f"embeddings/{face_id}_{sample_idx}.npy")

            # 샘플별 원본 이미지는 보관하지 않습니다. 기존 프로필에 썸네일이
            # 없을 때만 전달된 최소 이미지를 한 번 저장합니다.
            if face_image is not None and not face_data.get('image_path'):
                image_path = os.path.join(self.faces_dir, f"{face_id}.jpg")
                self._write_thumbnail_exclusive(image_path, face_image)
                thumbnail_path = image_path
                face_data['image_path'] = f"faces/{face_id}.jpg"
                face_data['image_paths'] = [f"faces/{face_id}.jpg"]

            # 샘플 카운트 증가
            face_data['sample_count'] = sample_idx + 1

            # 저장
            if not self.save():
                raise RuntimeError("Face store write failed")

            return True

        except Exception:
            if original_face_data is not None:
                self.faces[face_id] = original_face_data
            if embedding_path and os.path.isfile(embedding_path):
                try:
                    os.remove(embedding_path)
                except OSError:
                    logger.error("biometric_sample_rollback_failed")
            if thumbnail_path and os.path.isfile(thumbnail_path):
                try:
                    os.remove(thumbnail_path)
                except OSError:
                    logger.error("thumbnail_rollback_failed")
            logger.error("biometric_sample_add_failed")
            return False

    def find_match(
        self,
        embedding: np.ndarray,
        top_k: int = 1
    ) -> List[Tuple[str, float]]:
        """
        임베딩과 가장 유사한 얼굴 검색 (다중 임베딩 지원)

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
            # 다중 임베딩 경로 가져오기 (하위 호환성 유지)
            embedding_paths = face_data.get('embedding_paths')
            if not embedding_paths:
                # 기존 단일 임베딩 경로 사용
                embedding_paths = [face_data.get('embedding_path')]

            max_similarity = 0.0

            # 모든 임베딩과 비교하여 최고 유사도 사용
            for emb_path in embedding_paths:
                if not emb_path:
                    continue

                full_path = self._resolve_stored_path(
                    emb_path, self.embeddings_dir, {'.npy'}
                )
                if full_path is None:
                    continue

                stored_embedding = np.load(full_path, allow_pickle=False)

                # 유사도 계산
                emb1 = embedding.reshape(1, -1)
                emb2 = stored_embedding.reshape(1, -1)
                similarity = cosine_similarity(emb1, emb2)[0][0]

                # 최고 유사도 갱신
                max_similarity = max(max_similarity, similarity)

            if max_similarity > 0:
                similarities.append((face_id, float(max_similarity)))

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
        얼굴 삭제 (모든 샘플 포함)

        Args:
            face_id (str): 삭제할 얼굴 ID

        Returns:
            bool: 삭제 성공 여부
        """
        if face_id not in self.faces:
            return False

        try:
            face_data = self.faces[face_id]
            paths_to_delete: List[Path] = []

            embedding_paths = face_data.get('embedding_paths', [face_data.get('embedding_path')])
            for emb_path in embedding_paths:
                if emb_path:
                    full_path = self._resolve_stored_path(
                        emb_path, self.embeddings_dir, {'.npy'}
                    )
                    if full_path is not None:
                        paths_to_delete.append(full_path)

            image_paths = face_data.get('image_paths', [face_data.get('image_path')])
            for img_path in image_paths:
                if img_path:
                    full_path = self._resolve_stored_path(
                        img_path, self.faces_dir, {'.jpg', '.jpeg'}
                    )
                    if full_path is not None:
                        paths_to_delete.append(full_path)

            # Remove artifacts while the persisted metadata still identifies
            # them. If one unlink fails, a later request can safely retry rather
            # than leaving an unreferenced biometric file behind.
            for path in set(paths_to_delete):
                try:
                    os.remove(path)
                except OSError:
                    logger.error("biometric_artifact_deletion_failed")
                    return False

            del self.faces[face_id]
            if not self.save():
                self.faces[face_id] = face_data
                return False

            return True

        except Exception:
            logger.error("biometric_deletion_failed")
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

        original_metadata = copy.deepcopy(self.faces[face_id]['metadata'])
        self.faces[face_id]['metadata'].update(metadata)
        if self.save():
            return True
        self.faces[face_id]['metadata'] = original_metadata
        return False

    def merge_faces_by_name(self, name: str) -> Optional[str]:
        """
        같은 이름을 가진 모든 얼굴을 하나로 통합

        Args:
            name (str): 통합할 이름

        Returns:
            Optional[str]: 통합된 메인 face_id 또는 None (실패시)
        """
        # 같은 이름을 가진 모든 얼굴 찾기
        matching_faces = []
        for face_id, face_data in self.faces.items():
            if face_data.get('name') == name:
                matching_faces.append((face_id, face_data))

        if len(matching_faces) <= 1:
            return None

        # 가장 오래된 얼굴을 메인으로 선택 (registered_at 기준)
        matching_faces.sort(key=lambda x: x[1].get('registered_at', ''))
        main_face_id, main_face_data = matching_faces[0]

        try:
            # 나머지 얼굴들의 샘플을 메인 얼굴에 추가
            for face_id, face_data in matching_faces[1:]:
                # 모든 임베딩 가져오기
                embedding_paths = face_data.get('embedding_paths', [face_data.get('embedding_path')])
                image_paths = face_data.get('image_paths', [face_data.get('image_path')])

                for i, emb_path in enumerate(embedding_paths):
                    if not emb_path:
                        continue

                    # 임베딩 로드
                    full_emb_path = self._resolve_stored_path(
                        emb_path, self.embeddings_dir, {'.npy'}
                    )
                    if full_emb_path is None:
                        continue

                    embedding = np.load(full_emb_path, allow_pickle=False)

                    # 이미지 로드 (있으면)
                    face_image = None
                    if i < len(image_paths) and image_paths[i]:
                        full_img_path = self._resolve_stored_path(
                            image_paths[i], self.faces_dir, {'.jpg', '.jpeg'}
                        )
                        if full_img_path is not None:
                            face_image = cv2.imread(str(full_img_path))

                    # 메인 얼굴에 샘플 추가
                    self.add_face_sample(main_face_id, embedding, face_image)

                # 원본 얼굴 삭제
                self.remove_face(face_id)

            return main_face_id

        except Exception:
            logger.error("biometric_merge_failed")
            return None

    def get_all_faces(self) -> List[Dict]:
        """
        등록된 모든 얼굴 정보 반환

        Returns:
            List[Dict]: 얼굴 정보 리스트
        """
        return list(self.faces.values())

    def get_thumbnail_path(self, face_id: str) -> Optional[str]:
        """Resolve one server-owned thumbnail path without exposing layout."""
        face_data = self.faces.get(face_id)
        if not face_data:
            return None
        relative_path = face_data.get('image_path')
        if not relative_path:
            return None

        resolved = self._resolve_stored_path(
            relative_path, self.faces_dir, {'.jpg', '.jpeg'}
        )
        return str(resolved) if resolved is not None else None

    def save(self) -> bool:
        """
        데이터베이스 저장

        Returns:
            bool: 저장 성공 여부
        """
        temp_path = None
        try:
            if self._load_failed:
                raise RuntimeError("Refusing to overwrite an unreadable face store")
            if Path(self.db_path).is_symlink():
                raise RuntimeError("Face database cannot be a symbolic link")
            db_data = {
                'version': '1.0',
                'created_at': datetime.now().isoformat(),
                'last_updated': datetime.now().isoformat(),
                'faces': self.faces,
                'config': self.config
            }

            file_descriptor, temp_path = tempfile.mkstemp(
                prefix=".face-database-",
                suffix=".tmp",
                dir=self.data_dir,
            )
            if os.name == "posix":
                os.chmod(temp_path, 0o600)
            with os.fdopen(file_descriptor, 'w', encoding='utf-8') as f:
                json.dump(db_data, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_path, self.db_path)
            temp_path = None
            ensure_private_file(self.db_path)

            return True

        except Exception:
            if temp_path and os.path.isfile(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    logger.error("face_store_temp_cleanup_failed")
            logger.error("face_store_save_failed")
            return False

    def load(self) -> bool:
        """
        데이터베이스 로드

        Returns:
            bool: 로드 성공 여부
        """
        if not os.path.exists(self.db_path):
            return False

        try:
            if Path(self.db_path).is_symlink() or not Path(self.db_path).is_file():
                raise RuntimeError("Face database must be a regular file")
            with open(self.db_path, 'r', encoding='utf-8') as f:
                db_data = json.load(f)
            ensure_private_file(self.db_path)

            self.faces = db_data.get('faces', {})
            self.config = db_data.get('config', self.config)

            # config에서 threshold 로드
            if 'threshold' in self.config:
                self.threshold = self.config['threshold']

            return True

        except Exception:
            self._load_failed = True
            logger.error("face_store_load_failed")
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
            'model_name': self.config.get('model_name', 'default'),
        }

    @property
    def is_available(self) -> bool:
        """Whether the persisted metadata store was loaded without corruption."""
        return not self._load_failed

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
