"""
FastAPI 서버 애플리케이션

얼굴 인식 시스템 웹 API 서버
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

# API 라우트 import
from api.routes import router, cleanup_resources


# ==================== 애플리케이션 라이프사이클 ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    애플리케이션 라이프사이클 관리

    시작 시: 리소스 초기화
    종료 시: 리소스 정리
    """
    # 시작
    print("=" * 60)
    print("얼굴 인식 API 서버 시작 중...")
    print("=" * 60)

    # 초기 로드 (의존성이 자동으로 초기화됨)
    print("✓ API 라우트 로드 완료")

    yield

    # 종료
    print("\n" + "=" * 60)
    print("서버 종료 중...")
    cleanup_resources()
    print("✓ 리소스 정리 완료")
    print("=" * 60)


# ==================== FastAPI 애플리케이션 생성 ====================

app = FastAPI(
    title="얼굴 인식 API",
    description="실시간 얼굴 감지 및 인식 시스템 API",
    version="1.0.0",
    lifespan=lifespan
)


# ==================== CORS 설정 ====================

# CORS 허용 오리진 (프론트엔드 개발 시 필요)
origins = [
    "http://localhost:3000",  # React 기본 포트
    "http://localhost:5173",  # Vite 기본 포트
    "http://localhost:8080",  # Vue.js 기본 포트
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # 허용할 오리진
    allow_credentials=True,  # 쿠키 포함 허용
    allow_methods=["*"],  # 모든 HTTP 메서드 허용
    allow_headers=["*"],  # 모든 헤더 허용
)


# ==================== 라우터 등록 ====================

app.include_router(router)


# ==================== 루트 엔드포인트 ====================

@app.get("/")
async def root():
    """
    루트 엔드포인트

    API 정보 및 사용 가능한 엔드포인트 안내
    """
    return {
        "message": "얼굴 인식 API 서버",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "endpoints": {
            "health_check": "GET /api/health",
            "register_face": "POST /api/face/register",
            "list_faces": "GET /api/faces/list",
            "delete_face": "DELETE /api/face/{face_id}",
            "video_stream": "GET /api/camera/stream"
        }
    }


# ==================== 메인 함수 ====================

def main():
    """
    서버 실행 함수

    개발 모드로 Uvicorn 서버 시작
    """
    print("\n" + "=" * 60)
    print("🚀 FastAPI 서버를 시작합니다...")
    print("=" * 60)
    print("📡 서버 주소: http://localhost:8000")
    print("📚 API 문서: http://localhost:8000/docs")
    print("📖 ReDoc: http://localhost:8000/redoc")
    print("=" * 60)
    print("\n종료하려면 Ctrl+C를 누르세요.\n")

    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 개발 모드: 코드 변경 시 자동 재시작
        log_level="info"
    )


if __name__ == "__main__":
    main()
