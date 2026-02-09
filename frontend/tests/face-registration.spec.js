import { test, expect } from '@playwright/test';

/**
 * 얼굴 등록 프로세스 E2E 테스트
 */
test.describe('얼굴 등록 프로세스', () => {
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

        // Canvas를 애니메이션으로 업데이트 (실제 비디오처럼 보이도록)
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
      const originalGetUserMedia = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
      navigator.mediaDevices.getUserMedia = async (constraints) => {
        console.log('Mock getUserMedia called with:', constraints);

        // 실제 비디오 스트림 생성
        const stream = createFakeVideoStream();

        return stream;
      };
    });

    // 얼굴 등록 페이지로 이동
    await page.goto('/register');
  });

  test('카메라 시작 및 촬영', async ({ page }) => {
    // 페이지 제목 확인
    await expect(page.locator('h2')).toContainText('얼굴 등록');

    // 카메라 시작 버튼 확인
    const startButton = page.locator('button:has-text("카메라 시작")');
    await expect(startButton).toBeVisible();

    // 카메라 시작
    await startButton.click();

    // 비디오 엘리먼트가 표시되는지 확인 (최대 3초 대기)
    await expect(page.locator('video')).toBeVisible({ timeout: 3000 });

    // 촬영 버튼이 나타나는지 확인
    const captureButton = page.locator('button:has-text("촬영")');
    await expect(captureButton).toBeVisible();

    // 촬영 가이드 확인
    await expect(page.locator('text=촬영 가이드')).toBeVisible();

    // 촬영 버튼 클릭
    await captureButton.click();

    // 캡처된 이미지가 표시되는지 확인
    await expect(page.locator('img[alt="Captured"]')).toBeVisible({ timeout: 2000 });

    // 다시 촬영 버튼 확인
    await expect(page.locator('button:has-text("다시 촬영")')).toBeVisible();
  });

  test('스페이스바로 촬영', async ({ page }) => {
    // 카메라 시작
    await page.locator('button:has-text("카메라 시작")').click();
    await expect(page.locator('video')).toBeVisible({ timeout: 3000 });

    // 스페이스바로 촬영
    await page.keyboard.press('Space');

    // 캡처된 이미지 확인
    await expect(page.locator('img[alt="Captured"]')).toBeVisible({ timeout: 2000 });
  });

  test('전체 등록 프로세스', async ({ page }) => {
    // 1단계: 카메라 시작
    await page.locator('button:has-text("카메라 시작")').click();
    await expect(page.locator('video')).toBeVisible({ timeout: 3000 });

    // 등록 절차 1단계 활성화 확인
    const step1 = page.locator('text=카메라 시작').locator('..').locator('..');
    await expect(step1.locator('.bg-green-500')).toBeVisible();

    // 2단계: 촬영
    await page.keyboard.press('Space');
    await expect(page.locator('img[alt="Captured"]')).toBeVisible({ timeout: 2000 });

    // 등록 절차 2단계 활성화 확인
    const step2 = page.locator('text=얼굴 촬영').locator('..').locator('..');
    await expect(step2.locator('.bg-green-500')).toBeVisible();

    // 3단계: 이름 입력
    const nameInput = page.locator('input#name');
    await expect(nameInput).toBeEnabled();
    await nameInput.fill('테스트 사용자');

    // 등록 절차 3단계 활성화 확인
    const step3 = page.locator('text=이름 입력').locator('..').locator('..');
    await expect(step3.locator('.bg-green-500')).toBeVisible();

    // 4단계: 등록 버튼 활성화 확인
    const registerButton = page.locator('button:has-text("얼굴 등록")');
    await expect(registerButton).toBeEnabled();
  });

  test('다시 촬영 기능', async ({ page }) => {
    // 카메라 시작 및 촬영
    await page.locator('button:has-text("카메라 시작")').click();
    await expect(page.locator('video')).toBeVisible({ timeout: 3000 });
    await page.keyboard.press('Space');
    await expect(page.locator('img[alt="Captured"]')).toBeVisible({ timeout: 2000 });

    // 다시 촬영 버튼 클릭
    await page.locator('button:has-text("다시 촬영")').click();

    // 다시 비디오가 표시되는지 확인
    await expect(page.locator('video')).toBeVisible({ timeout: 3000 });

    // 캡처된 이미지가 사라졌는지 확인
    await expect(page.locator('img[alt="Captured"]')).not.toBeVisible();

    // 이름 입력 필드가 비활성화되었는지 확인
    await expect(page.locator('input#name')).toBeDisabled();
  });

  test('이름 입력 유효성 검사', async ({ page }) => {
    // 카메라 시작 및 촬영
    await page.locator('button:has-text("카메라 시작")').click();
    await expect(page.locator('video')).toBeVisible({ timeout: 3000 });
    await page.keyboard.press('Space');
    await expect(page.locator('img[alt="Captured"]')).toBeVisible({ timeout: 2000 });

    // 이름 없이 등록 시도
    const registerButton = page.locator('button:has-text("얼굴 등록")');
    await expect(registerButton).toBeDisabled();

    // 공백만 입력
    await page.locator('input#name').fill('   ');
    await expect(registerButton).toBeDisabled();

    // 유효한 이름 입력
    await page.locator('input#name').fill('홍길동');
    await expect(registerButton).toBeEnabled();
  });

  test('등록 절차 진행 상태 표시', async ({ page }) => {
    // 초기 상태: 모든 단계가 비활성화
    const steps = page.locator('.w-8.h-8.rounded-full');

    // 1단계: 카메라 시작
    await page.locator('button:has-text("카메라 시작")').click();
    await expect(page.locator('video')).toBeVisible({ timeout: 3000 });

    // 1단계 활성화 확인
    await expect(steps.nth(0)).toHaveClass(/bg-green-500/);

    // 2단계: 촬영
    await page.keyboard.press('Space');
    await expect(page.locator('img[alt="Captured"]')).toBeVisible({ timeout: 2000 });

    // 2단계 활성화 확인
    await expect(steps.nth(1)).toHaveClass(/bg-green-500/);

    // 3단계: 이름 입력
    await page.locator('input#name').fill('테스트');

    // 3단계 활성화 확인
    await expect(steps.nth(2)).toHaveClass(/bg-green-500/);
  });

  test('카메라 취소 기능', async ({ page }) => {
    // 카메라 시작
    await page.locator('button:has-text("카메라 시작")').click();
    await expect(page.locator('video')).toBeVisible({ timeout: 3000 });

    // 취소 버튼 클릭
    await page.locator('button:has-text("취소")').click();

    // 비디오가 사라졌는지 확인
    await expect(page.locator('video')).not.toBeVisible();

    // 카메라 시작 버튼이 다시 표시되는지 확인
    await expect(page.locator('button:has-text("카메라 시작")')).toBeVisible();
  });
});

/**
 * UI 요소 테스트
 */
test.describe('얼굴 등록 UI', () => {
  test.beforeEach(async ({ page, context, browserName }) => {
    if (browserName !== 'webkit') {
      await context.grantPermissions(['camera']);
    }
    await page.goto('/register');
  });

  test('페이지 로드 시 기본 요소 표시', async ({ page }) => {
    // 제목
    await expect(page.locator('h2')).toContainText('얼굴 등록');
    await expect(page.locator('text=실시간 카메라로 얼굴을 등록하세요')).toBeVisible();

    // 카메라 시작 버튼
    await expect(page.locator('button:has-text("카메라 시작")')).toBeVisible();

    // 등록 절차 안내
    await expect(page.locator('text=등록 절차')).toBeVisible();
    await expect(page.locator('p:has-text("카메라 시작")').first()).toBeVisible();
    await expect(page.locator('p:has-text("얼굴 촬영")').first()).toBeVisible();
    await expect(page.locator('p:has-text("이름 입력")').first()).toBeVisible();
    await expect(page.locator('p:has-text("등록 완료")').first()).toBeVisible();

    // 등록 정보 섹션
    await expect(page.locator('text=등록 정보')).toBeVisible();

    // 이름 입력 필드 (초기 비활성화)
    await expect(page.locator('input#name')).toBeDisabled();
  });

  test('반응형 레이아웃', async ({ page }) => {
    // 데스크톱 크기
    await page.setViewportSize({ width: 1920, height: 1080 });
    await expect(page.locator('.lg\\:col-span-2')).toBeVisible();

    // 태블릿 크기
    await page.setViewportSize({ width: 768, height: 1024 });
    await expect(page.locator('h2')).toBeVisible();

    // 모바일 크기
    await page.setViewportSize({ width: 375, height: 667 });
    await expect(page.locator('h2')).toBeVisible();
  });
});
