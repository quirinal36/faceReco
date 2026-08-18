# 얼굴 인식 시스템 - 프론트엔드

[English Documentation](./README.md)

얼굴 인식 시스템의 웹 대시보드 프론트엔드입니다.

## 기술 스택

- **React 19** - UI 라이브러리
- **Vite** - 빌드 도구 및 개발 서버
- **React Router v7** - 클라이언트 사이드 라우팅
- **Tailwind CSS** - 유틸리티 우선 CSS 프레임워크
- **Axios** - API 통신을 위한 HTTP 클라이언트
- **i18next** - 다국어 지원 (i18n) 프레임워크
- **Playwright** - E2E 테스트

## 시작하기

### 사전 요구사항

- Node.js 18+ 및 npm
- [보안 및 개인정보 운영 가이드](../docs/SECURITY.md)에 따라 operator와
  device 인증정보가 준비되고 `http://127.0.0.1:8000` loopback에서 실행 중인
  backend 서버

### 1. 의존성 설치

```bash
npm install
```

### 2. API 및 인증 설정

로컬 개발은 Vite의 same-origin `/api` proxy를 사용하므로 frontend 환경 파일이
필요하지 않습니다. UI를 별도로 호스팅하여 `VITE_API_URL`이 필요한 경우에도
공개 API origin만 설정할 수 있습니다. Vite는 `VITE_*` 값을 browser bundle에
노출하므로 operator/device token은 절대 넣지 마세요.

UI는 실행 시 Bearer 인증정보 하나를 입력받아 `/api/auth/whoami`로 역할을
확인한 뒤 현재 tab의 session storage에 보관합니다. Tab을 닫거나 API가 `401`을
반환하면 지워집니다. Token을 URL이나 query parameter에 넣지 마세요.

### 3. 개발 서버 실행

```bash
npm run dev
```

브라우저에서 [https://127.0.0.1:5173](https://127.0.0.1:5173)을 열고 필요하면
로컬 개발 인증서를 승인하세요. Vite와 backend는 모두 loopback에 bind하며
인터넷에 공개하면 안 됩니다.

## 주요 기능

### 대시보드 (`/`)
- **실시간 카메라 모니터링** - 백엔드로부터 실시간 비디오 스트림
- **얼굴 감지 및 인식** - 감지된 얼굴에 바운딩 박스 표시
- **통계 표시**
  - 감지된 얼굴 수
  - 인식된 얼굴 수
  - FPS (초당 프레임 수)

### 얼굴 등록 (`/register`)
- **카메라 촬영** - 웹캠을 사용하여 사진 촬영
- **얼굴 업로드** - 이름과 함께 새로운 얼굴 등록
- **중복 감지** - 중복 등록 방지

### 얼굴 목록 (`/faces`)
- **모든 얼굴 보기** - 등록된 모든 얼굴 탐색
- **얼굴 관리** - 데이터베이스에서 얼굴 삭제
- **중복 병합** - 중복 항목 통합

## 사용 가능한 스크립트

### 개발

```bash
# 핫 리로드와 함께 개발 서버 시작
npm run dev

# 코드 품질을 위한 ESLint 실행
npm run lint

# 프로덕션 빌드
npm run build

# 프로덕션 빌드 미리보기
npm run preview
```

### 테스트

```bash
# 모든 Playwright E2E 테스트 실행
npm test

# UI 모드로 테스트 실행
npm run test:ui

# headed 모드로 테스트 실행 (브라우저 표시)
npm run test:headed

# 테스트 디버깅
npm run test:debug

# 테스트 리포트 보기
npm run test:report
```

### 스크린샷

```bash
# 결정론적 synthetic screenshot만 캡처
FACERECO_SYNTHETIC_DOCS=1 npm run capture-screenshots
```

Capture script는 synthetic data flag가 없으면 실행을 거부하고 모든 API 호출을
가로챕니다. 실제 얼굴 또는 출석 저장소에서 문서 screenshot을 만들지 마세요.

## 프로젝트 구조

```
frontend/
├── src/
│   ├── components/          # 재사용 가능한 UI 컴포넌트
│   │   ├── Header.jsx       # 네비게이션 헤더
│   │   ├── Sidebar.jsx      # 사이드 네비게이션
│   │   ├── Layout.jsx       # 메인 레이아웃 래퍼
│   │   └── LanguageSwitcher.jsx  # 언어 토글
│   ├── pages/               # 페이지 컴포넌트
│   │   ├── Dashboard.jsx    # 실시간 모니터링
│   │   ├── FaceRegistration.jsx  # 얼굴 등록
│   │   └── FaceList.jsx     # 얼굴 관리
│   ├── services/            # API 서비스
│   │   └── api.js           # Axios API 클라이언트
│   ├── i18n/                # 다국어 지원
│   │   ├── i18n.js          # i18n 설정
│   │   ├── en.json          # 영어 번역
│   │   └── kr.json          # 한국어 번역
│   ├── main.jsx             # 애플리케이션 진입점
│   └── index.css            # 전역 스타일
├── tests/                   # Playwright E2E 테스트
│   ├── face-registration.spec.js
│   └── playwright.config.js
├── capture-screenshots.js   # 스크린샷 캡처 스크립트
├── package.json
├── vite.config.js
└── tailwind.config.js
```

## API 연동

프론트엔드는 Axios를 통해 백엔드 API와 통신합니다. Base URL은 환경 변수를 통해 설정됩니다.

### 사용되는 API 엔드포인트

- `GET /api/camera/stream` - 실시간 비디오 스트림 (MJPEG)
- `GET /api/camera/stats` - 실시간 통계
- `POST /api/face/register` - 새로운 얼굴 등록
- `GET /api/faces/list` - 등록된 모든 얼굴 목록
- `DELETE /api/face/{id}` - ID로 얼굴 삭제
- `POST /api/faces/merge` - 중복 얼굴 병합(이름은 JSON body로 전송)

자세한 API 문서는 [API 가이드](../docs/API_GUIDE.md)를 참고하세요.

## 다국어 지원 (i18n)

애플리케이션은 i18next를 사용하여 다국어를 지원합니다:

- 영어 (en)
- 한국어 (kr)

헤더의 언어 토글을 사용하여 언어를 전환할 수 있습니다.

### 새로운 언어 추가하기

1. `src/i18n/`에 새로운 번역 파일 생성 (예: `ja.json`)
2. 모든 키에 대한 번역 추가
3. `src/i18n/i18n.js`에서 import 및 등록
4. 언어 스위처 컴포넌트 업데이트

## 프로덕션 빌드

프로덕션용 애플리케이션 빌드:

```bash
npm run build
```

최적화된 파일이 `dist/` 디렉토리에 생성됩니다.

### 배포

빌드 결과는 loopback에서만 미리 봅니다:

```bash
# 로컬에서 프로덕션 빌드 미리보기
npm run preview
```

배포 시 보안 가이드의 승인된 same-origin loopback/TLS 서비스와 host firewall을
사용하세요. 임의의 공개 static server를 시작하거나 Vite API proxy를 외부에
노출하지 마세요.

## 테스트

E2E 테스트는 Playwright로 작성되었으며 다음을 포함합니다:

- 얼굴 등록 플로우
- 카메라 스트림 표시
- 얼굴 목록 관리
- API 오류 처리
- 하드웨어 없이 테스트 가능한 웹캠 모킹

테스트 실행:

```bash
# 모든 테스트
npm test

# UI와 함께
npm run test:ui

# 특정 테스트 파일
npx playwright test tests/face-registration.spec.js
```

## 브라우저 호환성

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

프로덕션 환경에서 웹캠 접근은 HTTPS가 필요합니다 (localhost 제외).

## 트러블슈팅

### 카메라 접근 문제

카메라가 작동하지 않는 경우:
- 브라우저 권한 확인
- HTTPS 확인 (프로덕션에 필요)
- 다른 브라우저 시도
- 백엔드 서버가 실행 중인지 확인

### CORS 오류

API 호출이 실패하는 경우:
- 백엔드 CORS 설정 확인
- 사용하는 경우 `VITE_API_URL`에는 API origin만 있고 token은 없는지 확인
- 백엔드 서버가 실행 중인지 확인

### 빌드 오류

```bash
# 캐시 삭제 및 재설치
rm -rf node_modules package-lock.json
npm install
```

## 기여하기

1. React 모범 사례 준수
2. 훅과 함께 함수형 컴포넌트 사용
3. 새로운 기능에 대한 테스트 작성
4. 커밋 전 린터 실행

## 라이선스

TBD

---

최종 업데이트: 2026-02-09
