# 테스트 실행 가이드

얼굴 인식 시스템의 Playwright E2E 테스트 실행 방법입니다.

## 🚀 빠른 시작

### 1. Playwright 설치

```bash
# 프론트엔드 디렉토리로 이동
cd frontend

# Playwright 설치
npm install -D @playwright/test

# 브라우저 설치
npx playwright install
```

### 2. 백엔드 서버 실행

테스트를 실행하기 전에 백엔드 API 서버를 먼저 실행해야 합니다:

```bash
# 새 터미널 창에서
cd backend
python app.py --mode server
```

서버가 `http://localhost:8000`에서 실행되는지 확인하세요.

### 3. 테스트 실행

```bash
# 프론트엔드 디렉토리에서
npm test
```

## 📋 테스트 모드

### UI 모드 (추천)
가장 편리한 방법으로, 인터랙티브 UI에서 테스트를 실행하고 디버깅할 수 있습니다:

```bash
npm run test:ui
```

**장점:**
- 각 테스트 단계를 시각적으로 확인
- 실시간 DOM 스냅샷 확인
- 특정 테스트만 선택하여 실행
- 시간 여행 디버깅 (타임라인 기능)

### 헤드풀 모드
브라우저를 실제로 띄워서 테스트가 실행되는 것을 볼 수 있습니다:

```bash
npm run test:headed
```

### 디버그 모드
테스트를 단계별로 실행하며 디버깅할 수 있습니다:

```bash
npm run test:debug
```

### 특정 테스트만 실행

```bash
# 특정 파일
npx playwright test face-registration.spec.js

# 특정 테스트 케이스
npx playwright test -g "스페이스바로 촬영"

# 특정 브라우저
npx playwright test --project=chromium
```

## 📊 테스트 리포트

테스트 실행 후 HTML 리포트를 확인할 수 있습니다:

```bash
npm run test:report
```

리포트에서 확인할 수 있는 정보:
- ✅ 통과한 테스트
- ❌ 실패한 테스트
- 📸 실패 시 스크린샷
- 🎥 실패 시 비디오 녹화
- 📝 상세한 실행 로그

## 🧪 테스트 커버리지

### 얼굴 등록 프로세스 (`face-registration.spec.js`)

#### 기능 테스트
- ✅ 카메라 시작 및 촬영
- ✅ 스페이스바로 촬영
- ✅ 전체 등록 프로세스 (4단계)
- ✅ 다시 촬영 기능
- ✅ 카메라 취소 기능

#### 유효성 검사
- ✅ 이름 입력 유효성 검사
- ✅ 빈 이름 처리
- ✅ 공백만 있는 이름 처리

#### UI 테스트
- ✅ 페이지 로드 시 기본 요소
- ✅ 등록 절차 진행 상태 표시
- ✅ 반응형 레이아웃 (모바일/태블릿/데스크톱)

### API 통합 테스트 (`face-registration-api.spec.js`)

#### 성공 시나리오
- ✅ 정상 등록 완료
- ✅ API 요청 데이터 검증
- ✅ 로딩 상태 확인

#### 실패 시나리오
- ✅ 얼굴 감지 실패
- ✅ 서버 오류 처리
- ✅ 네트워크 연결 실패
- ✅ 타임아웃 처리

## 🔧 설정

### `playwright.config.js`

주요 설정:
- **baseURL**: `http://localhost:5173` (Vite 개발 서버)
- **timeout**: 30초
- **프로젝트**: Chromium, Firefox, WebKit
- **카메라 권한**: 자동 허용
- **스크린샷/비디오**: 실패 시 자동 저장

### 웹캠 모킹

테스트에서는 실제 웹캠을 사용하지 않고 가짜 미디어 스트림을 사용합니다:

```javascript
navigator.mediaDevices.getUserMedia = async () => {
  // 가짜 비디오 스트림 반환
  return new MockMediaStream();
};
```

이렇게 하면:
- 실제 웹캠 없이도 테스트 가능
- CI/CD 환경에서도 실행 가능
- 테스트가 더 빠르고 안정적

## 🐛 트러블슈팅

### 백엔드 서버가 실행되지 않았을 때

```
Error: expect(received).toBeVisible()
```

**해결**: 백엔드 서버를 먼저 실행하세요.

```bash
cd backend
python app.py --mode server
```

### 브라우저가 설치되지 않았을 때

```
Error: browserType.launch: Executable doesn't exist
```

**해결**: 브라우저를 설치하세요.

```bash
npx playwright install
```

### 포트가 이미 사용 중일 때

```
Error: Port 5173 is already in use
```

**해결**:
1. 기존 프로세스 종료
2. 또는 다른 포트 사용 (vite.config.js 수정)

### 테스트가 타임아웃될 때

```
Error: Test timeout of 30000ms exceeded
```

**해결**:
1. 백엔드 서버 상태 확인
2. 네트워크 연결 확인
3. `playwright.config.js`에서 timeout 증가

## 💡 베스트 프랙티스

### 1. UI 모드 사용
개발 중에는 UI 모드를 사용하여 테스트를 실행하세요:
```bash
npm run test:ui
```

### 2. 특정 테스트만 실행
전체 테스트를 매번 실행하지 말고 작업 중인 테스트만 실행하세요:
```bash
npx playwright test -g "카메라 시작"
```

### 3. 헤드풀 모드로 디버깅
문제가 있을 때는 헤드풀 모드로 실행하여 브라우저에서 직접 확인하세요:
```bash
npm run test:headed
```

### 4. 리포트 활용
실패한 테스트의 스크린샷과 비디오를 확인하여 문제를 빠르게 파악하세요:
```bash
npm run test:report
```

## 📚 추가 자료

- [Playwright 공식 문서](https://playwright.dev/)
- [테스트 작성 가이드](https://playwright.dev/docs/writing-tests)
- [디버깅 가이드](https://playwright.dev/docs/debug)
- [CI/CD 통합](https://playwright.dev/docs/ci)

## 🎯 다음 단계

테스트 커버리지를 확장하려면:

1. **얼굴 목록 페이지 테스트** 추가
   - 목록 표시
   - 샘플 추가 기능
   - 삭제 기능

2. **대시보드 테스트** 추가
   - 통계 표시
   - 최근 인식 기록

3. **통합 시나리오 테스트**
   - 등록 → 목록 확인
   - 샘플 추가 → 인식 정확도 향상 확인

---

질문이나 문제가 있으면 이슈를 등록해주세요! 🚀
