# Face Recognition System - Frontend

얼굴 인식 시스템의 웹 대시보드 프론트엔드입니다.

## 기술 스택

- **React 19** - UI 라이브러리
- **Vite** - 빌드 도구
- **React Router v7** - 라우팅
- **Tailwind CSS v4** - 스타일링
- **Axios** - HTTP 클라이언트

## 시작하기

### 1. 의존성 설치

```bash
npm install
```

### 2. 환경 변수 설정

`.env` 파일에서 백엔드 API URL을 설정하세요:

```env
VITE_API_URL=http://localhost:8000
```

### 3. 개발 서버 실행

```bash
npm run dev
```

브라우저에서 [http://localhost:5173](http://localhost:5173)을 열어 확인하세요.

## 주요 기능

- **실시간 카메라 모니터링** (`/`) - 백엔드의 실시간 비디오 스트림 표시
- **얼굴 등록** (`/register`) - 새로운 얼굴 이미지 업로드 및 등록
- **얼굴 목록** (`/faces`) - 등록된 모든 얼굴 관리

## 프로덕션 빌드

```bash
npm run build
```

빌드된 파일은 `dist/` 폴더에 생성됩니다.
