import { expect, test as base } from '@playwright/test';

export const SYNTHETIC_OPERATOR_TOKEN = 'synthetic-playwright-operator-token-00000000';

export const test = base.extend({
  syntheticOperatorSession: [async ({ page }, use) => {
    await page.addInitScript((token) => {
      sessionStorage.setItem('facereco.auth.token', token);
      sessionStorage.setItem('facereco.auth.role', 'operator');
    }, SYNTHETIC_OPERATOR_TOKEN);

    await page.route('**/api/auth/whoami', async (route) => {
      const authorization = route.request().headers().authorization;
      await route.fulfill({
        status: authorization === `Bearer ${SYNTHETIC_OPERATOR_TOKEN}` ? 200 : 401,
        contentType: 'application/json',
        body: JSON.stringify(
          authorization === `Bearer ${SYNTHETIC_OPERATOR_TOKEN}`
            ? { role: 'operator' }
            : { detail: 'Authentication required' },
        ),
      });
    });

    await page.route('**/api/camera/release', (route) => route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ success: true }),
    }));
    await page.route('**/api/camera/reopen', (route) => route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ success: true }),
    }));
    await page.route('**/api/edu/students*', (route) => route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        students: [{ id: 'student-1', name: '테스트 사용자', school: '테스트중' }],
        total: 1,
      }),
    }));
    await page.route('**/api/edu/enrollments*', (route) => route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        month: '2026-08',
        enrollments: [{ id: 'enrollment-1', name: '테스트 사용자', subject: '수학', teacher: '선생님' }],
      }),
    }));

    await use();
  }, { auto: true }],
});

export { expect };
