export const SYNTHETIC_OPERATOR_TOKEN = 'synthetic-docs-operator-token-000000000000';

const SYNTHETIC_JPEG = Buffer.from(
  '/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////2wBDAf//////////////////////////////////////////////////////////////////////////////////////wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAX/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIQAxAAAAF//8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABBQJ//8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAgBAwEBPwF//8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAgBAgEBPwF//8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQAGPwJ//8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPyF//9oADAMBAAIAAwAAABD/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oACAEDAQE/EB//xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oACAECAQE/EB//xAAUEAEAAAAAAAAAAAAAAAAAAAAA/9oACAEBAAE/EB//2Q==',
  'base64',
);

const json = (route, body, status = 200) => route.fulfill({
  status,
  contentType: 'application/json',
  body: JSON.stringify(body),
});

export async function installSyntheticSession(page, language = 'ko') {
  await page.addInitScript(({ token, selectedLanguage }) => {
    sessionStorage.setItem('facereco.auth.token', token);
    sessionStorage.setItem('facereco.auth.role', 'operator');
    localStorage.setItem('language', selectedLanguage);
  }, { token: SYNTHETIC_OPERATOR_TOKEN, selectedLanguage: language });
}

export async function installSyntheticApi(page) {
  await page.route('**/api/**', async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    const authorization = request.headers().authorization;

    if (authorization !== `Bearer ${SYNTHETIC_OPERATOR_TOKEN}`) {
      await json(route, { detail: 'Authentication required' }, 401);
      return;
    }

    if (path === '/api/auth/whoami') {
      await json(route, { role: 'operator' });
      return;
    }

    if (path === '/api/faces/list') {
      await json(route, {
        total: 2,
        faces: [
          {
            face_id: 'synthetic-face-01',
            name: 'Synthetic Person 01',
            registered_at: '2026-01-02T09:00:00',
            last_seen: null,
            recognition_count: 4,
            sample_count: 1,
            thumbnail_url: '/api/faces/synthetic-face-01/thumbnail',
          },
          {
            face_id: 'synthetic-face-02',
            name: 'Synthetic Person 02',
            registered_at: '2026-01-03T09:00:00',
            last_seen: null,
            recognition_count: 2,
            sample_count: 1,
            thumbnail_url: '/api/faces/synthetic-face-02/thumbnail',
          },
        ],
      });
      return;
    }

    if (/^\/api\/faces\/[^/]+\/thumbnail$/.test(path)) {
      await route.fulfill({
        status: 200,
        contentType: 'image/jpeg',
        headers: { 'Cache-Control': 'private, no-store' },
        body: SYNTHETIC_JPEG,
      });
      return;
    }

    if (path.startsWith('/api/attendance/date/')) {
      await json(route, {
        total: 2,
        records: [
          { id: 1, face_id: 'synthetic-face-01', name: 'Synthetic Person 01', date: '2026-01-02', time: '09:00:00', confidence: 0.92 },
          { id: 2, face_id: 'synthetic-face-02', name: 'Synthetic Person 02', date: '2026-01-02', time: '09:05:00', confidence: 0.88 },
        ],
      });
      return;
    }

    if (path === '/api/attendance/stats') {
      await json(route, {
        total_days: 1,
        total_records: 2,
        by_person: [
          { name: 'Synthetic Person 01', count: 1 },
          { name: 'Synthetic Person 02', count: 1 },
        ],
      });
      return;
    }

    if (path === '/api/camera/stats') {
      await json(route, {
        faces_detected: 0,
        faces_recognized: 0,
        fps: 30,
        recognized_faces: [],
      });
      return;
    }

    if (path === '/api/camera/stream') {
      const multipartFrame = Buffer.concat([
        Buffer.from('--frame\r\nContent-Type: image/jpeg\r\n\r\n'),
        SYNTHETIC_JPEG,
        Buffer.from('\r\n--frame--\r\n'),
      ]);
      await route.fulfill({
        status: 200,
        contentType: 'multipart/x-mixed-replace; boundary=frame',
        body: multipartFrame,
      });
      return;
    }

    if (path === '/api/camera/reopen' || path === '/api/camera/release') {
      await json(route, { success: true });
      return;
    }

    await json(route, { detail: 'Synthetic route not configured' }, 404);
  });
}
