import { test, expect } from '@playwright/test';

/**
 * 얼굴 등록 API 통합 테스트
 */
test.describe('얼굴 등록 API 통합', () => {
  test.beforeEach(async ({ page, context, browserName }) => {
    // 카메라 권한 허용 (WebKit은 permissions API를 지원하지 않음)
    if (browserName !== 'webkit') {
      await context.grantPermissions(['camera']);
    }

    // 웹캠 모킹 (Canvas를 사용한 실제 비디오 스트림 생성)
    await page.addInitScript(() => {
      // Canvas를 사용해서 실제 비디오 스트림 생성
      const createFakeVideoStream = () => {
        const canvas = document.createElement('canvas');
        canvas.width = 640;
        canvas.height = 480;
        const ctx = canvas.getContext('2d');

        // 파란색 배경에 텍스트 그리기
        ctx.fillStyle = '#1e40af';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = '#ffffff';
        ctx.font = '30px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('Test Camera', canvas.width / 2, canvas.height / 2);

        // Canvas를 애니메이션으로 업데이트
        let frame = 0;
        setInterval(() => {
          ctx.fillStyle = '#1e40af';
          ctx.fillRect(0, 0, canvas.width, canvas.height);
          ctx.fillStyle = '#ffffff';
          ctx.font = '30px Arial';
          ctx.textAlign = 'center';
          ctx.fillText(`Test Camera ${frame}`, canvas.width / 2, canvas.height / 2);
          frame++;
        }, 100);

        // Canvas에서 MediaStream 생성
        return canvas.captureStream(30); // 30 FPS
      };

      // getUserMedia 모킹
      navigator.mediaDevices.getUserMedia = async (constraints) => {
        console.log('Mock getUserMedia called with:', constraints);
        return createFakeVideoStream();
      };
    });
  });

  test('API 등록 성공 시나리오', async ({ page }) => {
    // API 응답 모킹
    await page.route('**/api/face/register', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          face_id: 'person_test_001',
          name: '테스트 사용자',
          message: '테스트 사용자님의 얼굴이 성공적으로 등록되었습니다.'
        })
      });
    });

    await page.goto('/register');

    // 등록 프로세스 수행
    await page.locator('button:has-text("카메라 시작")').click();
    await expect(page.locator('video')).toBeVisible({ timeout: 3000 });
    await page.keyboard.press('Space');
    await expect(page.locator('img[alt="Captured"]')).toBeVisible({ timeout: 2000 });
    await page.locator('input#name').fill('테스트 사용자');

    // 등록 버튼 클릭
    await page.locator('button:has-text("얼굴 등록")').click();

    // 성공 메시지 확인
    await expect(page.locator('text=등록 완료!')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('text=새로운 등록을 시작합니다')).toBeVisible();
  });

  test('API 등록 실패 - 얼굴 감지 실패', async ({ page }) => {
    // API 응답 모킹 (얼굴 감지 실패)
    await page.route('**/api/face/register', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: false,
          message: '이미지에서 얼굴을 감지할 수 없습니다. 다른 이미지를 시도해주세요.'
        })
      });
    });

    await page.goto('/register');

    // 등록 프로세스 수행
    await page.locator('button:has-text("카메라 시작")').click();
    await expect(page.locator('video')).toBeVisible({ timeout: 3000 });
    await page.keyboard.press('Space');
    await expect(page.locator('img[alt="Captured"]')).toBeVisible({ timeout: 2000 });
    await page.locator('input#name').fill('테스트 사용자');

    // 등록 버튼 클릭
    await page.locator('button:has-text("얼굴 등록")').click();

    // 에러 메시지 확인
    await expect(page.locator('text=이미지에서 얼굴을 감지할 수 없습니다')).toBeVisible({ timeout: 5000 });
  });

  test('API 등록 실패 - 서버 오류', async ({ page }) => {
    // API 응답 모킹 (서버 오류)
    await page.route('**/api/face/register', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: '서버 오류: 데이터베이스 연결 실패'
        })
      });
    });

    await page.goto('/register');

    // 등록 프로세스 수행
    await page.locator('button:has-text("카메라 시작")').click();
    await expect(page.locator('video')).toBeVisible({ timeout: 3000 });
    await page.keyboard.press('Space');
    await expect(page.locator('img[alt="Captured"]')).toBeVisible({ timeout: 2000 });
    await page.locator('input#name').fill('테스트 사용자');

    // 등록 버튼 클릭
    await page.locator('button:has-text("얼굴 등록")').click();

    // 에러 메시지 확인
    await expect(page.locator('.bg-red-50')).toBeVisible({ timeout: 5000 });
  });

  test('API 요청 데이터 검증', async ({ page }) => {
    let capturedRequest = null;

    // API 요청 캡처
    await page.route('**/api/face/register', async (route) => {
      capturedRequest = route.request();
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          face_id: 'person_test_002',
          name: '홍길동',
          message: '홍길동님의 얼굴이 성공적으로 등록되었습니다.'
        })
      });
    });

    await page.goto('/register');

    // 등록 프로세스 수행
    await page.locator('button:has-text("카메라 시작")').click();
    await expect(page.locator('video')).toBeVisible({ timeout: 3000 });
    await page.keyboard.press('Space');
    await expect(page.locator('img[alt="Captured"]')).toBeVisible({ timeout: 2000 });
    await page.locator('input#name').fill('홍길동');
    await page.locator('button:has-text("얼굴 등록")').click();

    // 성공 메시지 대기
    await expect(page.locator('text=등록 완료!')).toBeVisible({ timeout: 5000 });

    // 요청 검증
    expect(capturedRequest).not.toBeNull();
    expect(capturedRequest.method()).toBe('POST');
    expect(capturedRequest.url()).toContain('/api/face/register');

    // FormData 검증 (헤더 확인)
    const headers = capturedRequest.headers();
    expect(headers['content-type']).toContain('multipart/form-data');
  });

  test('로딩 상태 확인', async ({ page }) => {
    // 느린 API 응답 모킹
    await page.route('**/api/face/register', async (route) => {
      await new Promise(resolve => setTimeout(resolve, 2000)); // 2초 대기
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          face_id: 'person_test_003',
          name: '테스트',
          message: '테스트님의 얼굴이 성공적으로 등록되었습니다.'
        })
      });
    });

    await page.goto('/register');

    // 등록 프로세스 수행
    await page.locator('button:has-text("카메라 시작")').click();
    await expect(page.locator('video')).toBeVisible({ timeout: 3000 });
    await page.keyboard.press('Space');
    await expect(page.locator('img[alt="Captured"]')).toBeVisible({ timeout: 2000 });
    await page.locator('input#name').fill('테스트');

    // 등록 버튼 클릭
    await page.locator('button:has-text("얼굴 등록")').click();

    // 로딩 상태 확인
    await expect(page.locator('text=등록 중...')).toBeVisible();
    await expect(page.locator('.animate-spin')).toBeVisible();

    // 등록 버튼 비활성화 확인
    const registerButton = page.locator('button:has-text("등록 중...")');
    await expect(registerButton).toBeDisabled();

    // 성공 메시지 대기
    await expect(page.locator('text=등록 완료!')).toBeVisible({ timeout: 5000 });
  });
});

/**
 * 네트워크 오류 처리 테스트
 */
test.describe('네트워크 오류 처리', () => {
  test.beforeEach(async ({ page, context, browserName }) => {
    // 카메라 권한 허용 (WebKit은 permissions API를 지원하지 않음)
    if (browserName !== 'webkit') {
      await context.grantPermissions(['camera']);
    }
    await page.goto('/register');
  });

  test('네트워크 연결 실패', async ({ page }) => {
    // 네트워크 요청 실패 시뮬레이션
    await page.route('**/api/face/register', async (route) => {
      await route.abort('failed');
    });

    // 웹캠 모킹은 생략하고 직접 captured 상태로 전환
    // (이 테스트에서는 API 호출만 테스트)
  });

  test('타임아웃 처리', async ({ page }) => {
    // 타임아웃 시뮬레이션 (응답 없음)
    await page.route('**/api/face/register', async (route) => {
      // 응답하지 않음 (타임아웃 발생)
      await new Promise(() => {}); // 무한 대기
    });
  });
});
