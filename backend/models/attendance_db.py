"""
출석 데이터베이스 모듈

SQLite를 사용한 출석 기록 저장 및 관리
- 같은 날짜의 동일 인물은 1회만 기록 (UNIQUE 제약조건)
"""

import os
import sqlite3
from typing import Optional, List, Dict
from datetime import datetime, date


class AttendanceDB:
    """
    출석 데이터베이스 관리 클래스

    SQLite를 사용하여 출석 기록을 저장하고 조회합니다.
    UNIQUE(face_id, date) 제약조건으로 동일 인물 당일 중복 기록을 방지합니다.
    """

    def __init__(self, db_path: str = "data/attendance.db"):
        """
        출석 데이터베이스 초기화

        Args:
            db_path: 데이터베이스 파일 경로 (상대 경로, backend 디렉토리 기준)
        """
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.db_path = os.path.join(backend_dir, db_path)

        # 디렉토리 생성
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        # 테이블 생성
        self._create_tables()

    def _get_connection(self) -> sqlite3.Connection:
        """SQLite 연결 생성 (thread-safe)"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _create_tables(self) -> None:
        """출석 테이블 생성"""
        conn = self._get_connection()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    face_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    date DATE NOT NULL,
                    time TIME NOT NULL,
                    confidence REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(face_id, date)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_attendance_name ON attendance(name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_attendance_face_date ON attendance(face_id, date)")
            conn.commit()
            print(f"출석 데이터베이스 초기화 완료: {self.db_path}")
        finally:
            conn.close()

    def record_attendance(self, face_id: str, name: str, confidence: float = 0.0) -> bool:
        """
        출석 기록 (당일 중복 방지)

        INSERT OR IGNORE로 같은 날짜에 동일 face_id는 무시됩니다.

        Args:
            face_id: 얼굴 ID
            name: 이름
            confidence: 인식 신뢰도

        Returns:
            True면 새로 기록됨, False면 이미 기록되어 무시됨
        """
        now = datetime.now()
        today = now.strftime('%Y-%m-%d')
        current_time = now.strftime('%H:%M:%S')

        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "INSERT OR IGNORE INTO attendance (face_id, name, date, time, confidence) VALUES (?, ?, ?, ?, ?)",
                (face_id, name, today, current_time, confidence)
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def get_today_attendance(self) -> List[Dict]:
        """오늘 출석 현황 조회"""
        today = date.today().strftime('%Y-%m-%d')
        return self.get_attendance_by_date(today)

    def get_attendance_by_date(self, target_date: str) -> List[Dict]:
        """
        특정 날짜 출석 조회

        Args:
            target_date: 날짜 (YYYY-MM-DD)

        Returns:
            출석 기록 리스트
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM attendance WHERE date = ? ORDER BY time ASC",
                (target_date,)
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_attendance_range(self, start_date: str, end_date: str) -> List[Dict]:
        """
        기간별 출석 조회

        Args:
            start_date: 시작 날짜 (YYYY-MM-DD)
            end_date: 종료 날짜 (YYYY-MM-DD)

        Returns:
            출석 기록 리스트
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM attendance WHERE date BETWEEN ? AND ? ORDER BY date DESC, time ASC",
                (start_date, end_date)
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_attendance_by_name(
        self,
        name: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict]:
        """
        특정 인물 출석 이력 조회

        Args:
            name: 이름
            start_date: 시작 날짜 (선택)
            end_date: 종료 날짜 (선택)

        Returns:
            출석 기록 리스트
        """
        conn = self._get_connection()
        try:
            if start_date and end_date:
                cursor = conn.execute(
                    "SELECT * FROM attendance WHERE name = ? AND date BETWEEN ? AND ? ORDER BY date DESC, time ASC",
                    (name, start_date, end_date)
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM attendance WHERE name = ? ORDER BY date DESC, time ASC",
                    (name,)
                )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_attendance_stats(self, start_date: str, end_date: str) -> Dict:
        """
        출석 통계 조회

        Args:
            start_date: 시작 날짜
            end_date: 종료 날짜

        Returns:
            통계 정보 (총 기록수, 인물별 출석 횟수 등)
        """
        conn = self._get_connection()
        try:
            # 총 기록 수
            cursor = conn.execute(
                "SELECT COUNT(*) as total FROM attendance WHERE date BETWEEN ? AND ?",
                (start_date, end_date)
            )
            total = cursor.fetchone()['total']

            # 인물별 출석 횟수
            cursor = conn.execute(
                """SELECT name, COUNT(*) as count,
                          MIN(date) as first_date, MAX(date) as last_date
                   FROM attendance
                   WHERE date BETWEEN ? AND ?
                   GROUP BY name
                   ORDER BY count DESC""",
                (start_date, end_date)
            )
            by_person = [dict(row) for row in cursor.fetchall()]

            # 기간 내 고유 날짜 수
            cursor = conn.execute(
                "SELECT COUNT(DISTINCT date) as total_days FROM attendance WHERE date BETWEEN ? AND ?",
                (start_date, end_date)
            )
            total_days = cursor.fetchone()['total_days']

            return {
                'start_date': start_date,
                'end_date': end_date,
                'total_records': total,
                'total_days': total_days,
                'by_person': by_person
            }
        finally:
            conn.close()

    def delete_attendance(self, record_id: int) -> bool:
        """
        출석 기록 삭제

        Args:
            record_id: 기록 ID

        Returns:
            삭제 성공 여부
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute("DELETE FROM attendance WHERE id = ?", (record_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def is_checked_in_today(self, face_id: str) -> bool:
        """
        오늘 출석 여부 확인

        Args:
            face_id: 얼굴 ID

        Returns:
            오늘 이미 출석했으면 True
        """
        today = date.today().strftime('%Y-%m-%d')
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT COUNT(*) as cnt FROM attendance WHERE face_id = ? AND date = ?",
                (face_id, today)
            )
            return cursor.fetchone()['cnt'] > 0
        finally:
            conn.close()

    def get_today_count(self) -> int:
        """오늘 출석 인원 수"""
        today = date.today().strftime('%Y-%m-%d')
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT COUNT(*) as cnt FROM attendance WHERE date = ?",
                (today,)
            )
            return cursor.fetchone()['cnt']
        finally:
            conn.close()
