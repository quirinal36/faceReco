# Playwright 테스트 가이드

## 설치

Playwright 설치:
```bash
npm install -D @playwright/test
npx playwright install
```

## 테스트 실행

### 기본 테스트 실행
```bash
npm test
```

### UI 모드로 실행 (권장)
인터랙티브한 UI에서 테스트를 실행하고 디버깅할 수 있습니다:
```bash
npm run test:ui
```

### 헤드풀 모드 (브라우저를 실제로 띄워서 실행)
```bash
npm run test:headed
```

### 디버그 모드
```bash
npm run test:debug
```

### 특정 테스트 파일만 실행
```bash
npx playwright test face-registration.spec.js
```

### 특정 브라우저에서만 실행
```bash
npx playwright test --project=chromium
npx playwright test --project=firefox
npx playwright test --project=webkit
```

## 테스트 리포트 확인

테스트 실행 후 HTML 리포트를 확인:
```bash
npm run test:report
```

## 테스트 구조

### `face-registration.spec.js`
얼굴 등록 프로세스의 E2E 테스트:

#### 주요 테스트 케이스
1. **카메라 시작 및 촬영**: 카메라 시작 버튼 클릭 후 촬영 기능 확인
2. **스페이스바로 촬영**: 키보드 단축키로 촬영 기능 확인
3. **전체 등록 프로세스**: 카메라 시작 → 촬영 → 이름 입력 → 등록 전체 흐름 확인
4. **다시 촬영 기능**: 촬영 후 다시 촬영 버튼 기능 확인
5. **이름 입력 유효성 검사**: 빈 이름, 공백 등 유효성 검사 확인
6. **등록 절차 진행 상태**: 4단계 진행 상태 UI 확인
7. **카메라 취소 기능**: 카메라 활성화 중 취소 기능 확인
8. **UI 요소 테스트**: 페이지 로드 시 기본 요소 확인
9. **반응형 레이아웃**: 다양한 화면 크기에서 레이아웃 확인

## 웹캠 모킹

테스트에서는 실제 웹캠 대신 가짜 미디어 스트림을 사용합니다:
- `navigator.mediaDevices.getUserMedia` 모킹
- 가짜 비디오 트랙 생성
- 비디오 엘리먼트에 가짜 스트림 연결

## 주의사항

### 백엔드 서버 실행
테스트 실행 전에 백엔드 서버가 실행 중이어야 합니다:
```bash
cd ../backend
python app.py --mode server
```

### 프론트엔드 개발 서버
Playwright 설정에서 자동으로 개발 서버를 시작하지만, 수동으로 실행할 수도 있습니다:
```bash
npm run dev
```

### 카메라 권한
테스트에서는 자동으로 카메라 권한을 부여합니다 (`playwright.config.js` 참조).

## 트러블슈팅

### 테스트 실패 시
1. 스크린샷 확인: `test-results/` 디렉토리에 실패한 테스트의 스크린샷이 저장됩니다
2. 비디오 확인: 실패한 테스트의 비디오 녹화가 저장됩니다
3. 트레이스 확인: `npx playwright show-trace` 명령어로 상세한 실행 과정 확인

### 브라우저 설치
특정 브라우저가 설치되지 않았다면:
```bash
npx playwright install chromium
npx playwright install firefox
npx playwright install webkit
```

## CI/CD 통합

GitHub Actions에서 실행하려면 `.github/workflows/playwright.yml` 파일 추가:
```yaml
name: Playwright Tests
on:
  push:
    branches: [ main, master ]
  pull_request:
    branches: [ main, master ]
jobs:
  test:
    timeout-minutes: 60
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-node@v4
      with:
        node-version: 20
    - name: Install dependencies
      run: npm ci
    - name: Install Playwright Browsers
      run: npx playwright install --with-deps
    - name: Run Playwright tests
      run: npm test
    - uses: actions/upload-artifact@v4
      if: always()
      with:
        name: playwright-report
        path: playwright-report/
        retention-days: 30
```
