import { expect, test } from '@playwright/test';

const OPERATOR_TOKEN = 'synthetic-security-operator-token-00000000';
const DEVICE_TOKEN = 'synthetic-security-device-token-0000000000';

async function installSession(page, token, role) {
  await page.addInitScript(({ storedToken, storedRole }) => {
    sessionStorage.setItem('facereco.auth.token', storedToken);
    sessionStorage.setItem('facereco.auth.role', storedRole);
  }, { storedToken: token, storedRole: role });
}

async function mockWhoami(page, token, role) {
  await page.route('**/api/auth/whoami', (route) => route.fulfill({
    status: route.request().headers().authorization === `Bearer ${token}` ? 200 : 401,
    contentType: 'application/json',
    body: JSON.stringify({ role }),
  }));
}

async function mockCameraControls(page) {
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
}

test('validates a runtime credential and exposes only the device route', async ({ page }) => {
  let authorization = null;
  await page.route('**/api/auth/whoami', (route) => {
    authorization = route.request().headers().authorization;
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ role: 'device' }),
    });
  });

  await page.goto('/');
  await page.locator('#runtime-credential').fill(DEVICE_TOKEN);
  await page.locator('form button[type="submit"]').click();

  await expect(page).toHaveURL(/\/liveness$/);
  expect(authorization).toBe(`Bearer ${DEVICE_TOKEN}`);
  await expect(page.locator('nav a')).toHaveCount(1);
  await expect(page.locator('nav a')).toHaveAttribute('href', '/liveness');
  await expect(page.locator('body')).not.toContainText(DEVICE_TOKEN);
  expect(page.url()).not.toContain(DEVICE_TOKEN);

  const stored = await page.evaluate(() => ({
    role: sessionStorage.getItem('facereco.auth.role'),
    token: sessionStorage.getItem('facereco.auth.token'),
  }));
  expect(stored).toEqual({ role: 'device', token: DEVICE_TOKEN });
});

test('an API 401 clears the session and returns to the credential gate', async ({ page }) => {
  await installSession(page, OPERATOR_TOKEN, 'operator');
  await mockWhoami(page, OPERATOR_TOKEN, 'operator');
  await page.route('**/api/faces/list', (route) => route.fulfill({
    status: 401,
    contentType: 'application/json',
    body: JSON.stringify({ detail: 'Authentication required' }),
  }));

  await page.goto('/faces');
  await expect(page.locator('#runtime-credential')).toBeVisible();
  expect(await page.evaluate(() => sessionStorage.getItem('facereco.auth.token'))).toBeNull();
  expect(await page.evaluate(() => sessionStorage.getItem('facereco.auth.role'))).toBeNull();
});

test('keeps sensitive identifiers in JSON request bodies', async ({ page }) => {
  await installSession(page, OPERATOR_TOKEN, 'operator');
  await mockWhoami(page, OPERATOR_TOKEN, 'operator');
  await mockCameraControls(page);

  const requests = {};
  for (const [key, endpoint] of Object.entries({
    merge: '/api/faces/merge',
    person: '/api/attendance/person/search',
    status: '/api/liveness/status',
  })) {
    await page.route(`**${endpoint}`, (route) => {
      requests[key] = {
        authorization: route.request().headers().authorization,
        body: route.request().postDataJSON(),
        method: route.request().method(),
        url: route.request().url(),
      };
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true }),
      });
    });
  }

  await page.goto('/register');
  await page.evaluate(async () => {
    const { faceAPI } = await import('/src/services/api.js');
    await faceAPI.mergeFacesByName('Synthetic Person');
    await faceAPI.getAttendanceByPerson('Synthetic Person', '2026-01-01', '2026-01-31');
    sessionStorage.setItem('facereco.auth.token', 'synthetic-security-device-token-0000000000');
    sessionStorage.setItem('facereco.auth.role', 'device');
    await faceAPI.getLivenessStatus('synthetic-session-id');
  });

  expect(requests.merge.body).toEqual({ name: 'Synthetic Person' });
  expect(requests.person.body).toEqual({
    name: 'Synthetic Person',
    start_date: '2026-01-01',
    end_date: '2026-01-31',
  });
  expect(requests.status.body).toEqual({ session_id: 'synthetic-session-id' });

  for (const request of [requests.merge, requests.person]) {
    expect(request.method).toBe('POST');
    expect(request.authorization).toBe(`Bearer ${OPERATOR_TOKEN}`);
    expect(request.url).not.toContain('Synthetic%20Person');
    expect(request.url).not.toContain('synthetic-session-id');
  }
  expect(requests.status.method).toBe('POST');
  expect(requests.status.authorization).toBe(`Bearer ${DEVICE_TOKEN}`);
  expect(requests.status.url).not.toContain('synthetic-session-id');
});

test('loads thumbnails as authenticated blobs and revokes their object URLs', async ({ page }) => {
  await installSession(page, OPERATOR_TOKEN, 'operator');
  await page.addInitScript(() => {
    window.__revokedObjectUrls = [];
    const revokeObjectUrl = URL.revokeObjectURL.bind(URL);
    URL.revokeObjectURL = (url) => {
      window.__revokedObjectUrls.push(url);
      revokeObjectUrl(url);
    };
  });
  await mockWhoami(page, OPERATOR_TOKEN, 'operator');
  await mockCameraControls(page);
  await page.route('**/api/faces/list', (route) => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      total: 1,
      faces: [{
        face_id: 'synthetic-face',
        name: 'Synthetic Person',
        registered_at: '2026-01-01T00:00:00',
        recognition_count: 0,
        sample_count: 1,
        thumbnail_url: '/api/faces/synthetic-face/thumbnail',
      }],
    }),
  }));

  let thumbnailAuthorization = null;
  await page.route('**/api/faces/synthetic-face/thumbnail', (route) => {
    thumbnailAuthorization = route.request().headers().authorization;
    return route.fulfill({
      status: 200,
      contentType: 'image/svg+xml',
      body: '<svg xmlns="http://www.w3.org/2000/svg" width="8" height="8"><rect width="8" height="8" fill="blue"/></svg>',
    });
  });

  await page.goto('/faces');
  const thumbnail = page.locator('img[alt="Synthetic Person"]');
  await expect(thumbnail).toHaveAttribute('src', /^blob:/);
  expect(thumbnailAuthorization).toBe(`Bearer ${OPERATOR_TOKEN}`);

  await page.locator('a[href="/register"]').click();
  await expect.poll(() => page.evaluate(() => window.__revokedObjectUrls.length)).toBeGreaterThan(0);
});

test('opens the MJPEG stream with a bearer header and no URL credential', async ({ page }) => {
  await installSession(page, OPERATOR_TOKEN, 'operator');
  await mockWhoami(page, OPERATOR_TOKEN, 'operator');
  await mockCameraControls(page);

  let streamRequest = null;
  await page.route('**/api/camera/stream', (route) => {
    streamRequest = route.request();
    const frame = Buffer.concat([
      Buffer.from('--frame\r\nContent-Type: image/jpeg\r\n\r\n'),
      Buffer.from([0xff, 0xd8, 0xff, 0xd9]),
      Buffer.from('\r\n--frame--\r\n'),
    ]);
    return route.fulfill({
      status: 200,
      contentType: 'multipart/x-mixed-replace; boundary=frame',
      body: frame,
    });
  });
  await page.route('**/api/camera/stats', (route) => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      faces_detected: 0,
      faces_recognized: 0,
      fps: 30,
      recognized_faces: [],
    }),
  }));

  await page.goto('/');
  await expect(page.locator('img[alt="Camera Stream"]')).toHaveAttribute('src', /^blob:/);
  expect(streamRequest.headers().authorization).toBe(`Bearer ${OPERATOR_TOKEN}`);
  expect(streamRequest.url()).toBe('https://127.0.0.1:5173/api/camera/stream');
  expect(streamRequest.url()).not.toContain(OPERATOR_TOKEN);
});
