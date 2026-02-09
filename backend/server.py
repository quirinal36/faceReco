"""
FastAPI 서버 애플리케이션

얼굴 인식 시스템 웹 API 서버
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import uvicorn
import os

# API 라우트 import
from api.routes import router, cleanup_resources


# ==================== 애플리케이션 라이프사이클 ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle management

    Startup: Initialize resources
    Shutdown: Cleanup resources
    """
    # Startup
    print("=" * 60)
    print("Starting Face Recognition API Server...")
    print("=" * 60)

    # Initial load (dependencies will be initialized automatically)
    print("API routes loaded successfully")

    yield

    # Shutdown
    print("\n" + "=" * 60)
    print("Shutting down server...")
    cleanup_resources()
    print("Resources cleaned up successfully")
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


# ==================== Static 파일 제공 ====================

# data 디렉토리를 static 파일로 마운트
data_dir = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(data_dir, exist_ok=True)

app.mount("/data", StaticFiles(directory=data_dir), name="data")


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
    print("Starting FastAPI server...")
    print("=" * 60)
    print("Server URL: http://localhost:8000")
    print("API Documentation: http://localhost:8000/docs")
    print("ReDoc: http://localhost:8000/redoc")
    print("=" * 60)
    print("\nPress Ctrl+C to stop the server.\n")

    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 개발 모드: 코드 변경 시 자동 재시작
        log_level="info"
    )


if __name__ == "__main__":
    main()
