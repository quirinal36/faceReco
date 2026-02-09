import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright 테스트 설정
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './tests',

  // 테스트 타임아웃 (30초)
  timeout: 30 * 1000,

  // 각 expect 타임아웃
  expect: {
    timeout: 5000
  },

  // 테스트 실행 옵션
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,

  // 리포터
  reporter: 'html',

  // 모든 테스트에 공통으로 적용되는 옵션
  use: {
    // 기본 URL
    baseURL: 'http://localhost:5173',

    // 스크린샷 옵션
    screenshot: 'only-on-failure',

    // 비디오 녹화
    video: 'retain-on-failure',

    // 트레이스
    trace: 'on-first-retry',
  },

  // 프로젝트별 설정
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        // 웹캠 권한 자동 허용
        permissions: ['camera'],
      },
    },

    {
      name: 'firefox',
      use: {
        ...devices['Desktop Firefox'],
        permissions: ['camera'],
      },
    },

    // WebKit은 permissions API를 지원하지 않으므로 카메라 권한 설정 제거
    {
      name: 'webkit',
      use: {
        ...devices['Desktop Safari'],
      },
    },
  ],

  // 개발 서버 설정
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
  },
});
