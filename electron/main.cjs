const { app, BrowserWindow, session, dialog } = require('electron');
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { startLocalServer } = require('./local-server.cjs');

let backend;
let server;
let window;
let origin;
const singleInstance = app.requestSingleInstanceLock();
if (!singleInstance) app.quit();
app.on('second-instance', () => { if (window) { window.restore(); window.focus(); } });

function backendReady() {
  return new Promise(resolve => {
    const req = http.get('http://127.0.0.1:8000/', res => {
      let body = '';
      res.on('data', chunk => { body += chunk; });
      res.on('end', () => {
        try { resolve(JSON.parse(body).message === '얼굴 인식 API 서버'); }
        catch { resolve(false); }
      });
    });
    req.setTimeout(1000, () => req.destroy());
    req.on('error', () => resolve(false));
  });
}

async function ensureBackend() {
  if (await backendReady()) return;
  const configPath = path.join(app.getAppPath(), 'runtime.json');
  const root = fs.existsSync(configPath)
    ? JSON.parse(fs.readFileSync(configPath, 'utf8')).workspace
    : path.resolve(__dirname, '..');
  const python = path.join(root, '.venv311/bin/python');
  if (!fs.existsSync(python)) throw new Error(`Python 환경을 찾을 수 없습니다: ${python}`);
  backend = spawn(python, ['-m', 'uvicorn', 'server:app', '--host', '127.0.0.1', '--port', '8000', '--timeout-graceful-shutdown', '3'], {
    cwd: path.join(root, 'backend'), stdio: ['ignore', 'pipe', 'pipe'],
  });
  const log = fs.createWriteStream(path.join(app.getPath('userData'), 'backend.log'), { flags: 'a' });
  backend.stdout.pipe(log, { end: false }); backend.stderr.pipe(log, { end: false });
  let launchError;
  backend.on('error', error => { launchError = error; });
  backend.on('exit', () => log.end());
  for (let i = 0; i < 120; i++) {
    if (launchError) throw launchError;
    if (backend.exitCode !== null) throw new Error('얼굴인식 서버 실행 실패. backend.log를 확인해주세요.');
    if (await backendReady()) return;
    await new Promise(resolve => setTimeout(resolve, 500));
  }
  throw new Error('얼굴인식 서버 시작 시간이 초과되었습니다.');
}

function createWindow() {
  window = new BrowserWindow({ width: 1360, height: 900, minWidth: 800, minHeight: 600,
    autoHideMenuBar: true, title: '얼굴 인식 시스템',
    webPreferences: { contextIsolation: true, nodeIntegration: false, sandbox: true },
  });
  window.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
  window.webContents.on('will-navigate', (event, url) => {
    if (new URL(url).origin !== origin) event.preventDefault();
  });
  window.on('page-title-updated', event => event.preventDefault());
  window.on('closed', () => { window = null; });
  window.loadURL(origin + (process.argv.includes('--demo') ? '/?demo=1' : '/'));
}

if (singleInstance) app.whenReady().then(async () => {
  await ensureBackend();
  server = await startLocalServer(path.join(app.getAppPath(), 'frontend/dist'));
  origin = `http://127.0.0.1:${server.address().port}`;
  session.defaultSession.setPermissionRequestHandler((contents, permission, callback) => {
    callback(permission === 'media' && contents.getURL().startsWith(origin + '/'));
  });
  session.defaultSession.setPermissionCheckHandler((_contents, permission, requestingOrigin) => {
    return permission === 'media' && requestingOrigin === origin;
  });
  createWindow();
  app.on('activate', () => { if (!window) createWindow(); });
}).catch(error => { dialog.showErrorBox('얼굴 인식 시스템 실행 오류', error.message); app.quit(); });

app.on('before-quit', () => {
  server?.close();
  if (backend && backend.exitCode === null) backend.kill('SIGTERM');
});
app.on('window-all-closed', () => app.quit());
