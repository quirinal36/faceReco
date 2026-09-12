// Build a local Linux app using the Electron runtime already installed here.
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const output = path.join(root, 'dist', `FaceReco-linux-${process.arch}`);
fs.mkdirSync(output, { recursive: true });
fs.cpSync(path.join(root, 'node_modules/electron/dist'), output, { recursive: true });
const target = path.join(output, 'resources/app');
fs.mkdirSync(path.join(target, 'electron'), { recursive: true });
for (const file of ['main.cjs', 'local-server.cjs']) fs.copyFileSync(path.join(__dirname, file), path.join(target, 'electron', file));
fs.cpSync(path.join(root, 'frontend/dist'), path.join(target, 'frontend/dist'), { recursive: true });
fs.writeFileSync(path.join(target, 'package.json'), JSON.stringify({ name: 'facereco', productName: 'FaceReco', version: '1.0.0', main: 'electron/main.cjs' }, null, 2));
fs.writeFileSync(path.join(target, 'runtime.json'), JSON.stringify({ workspace: root }, null, 2));
fs.renameSync(path.join(output, 'electron'), path.join(output, 'facereco'));
fs.writeFileSync(path.join(output, 'FaceReco.sh'), '#!/bin/sh\nunset ELECTRON_RUN_AS_NODE\ncd -- "$(dirname -- "$0")"\nexec ./facereco --no-sandbox "$@"\n', { mode: 0o755 });
fs.writeFileSync(path.join(output, 'README.txt'), 'FaceReco.sh를 실행하세요.\n이 컴퓨터 전용 Linux 빌드입니다. 웹 UI와 Electron은 포함되어 있습니다.\nPython 환경, 인식 모델, 얼굴 데이터는 기존 프로젝트의 것을 사용합니다.\n프로젝트 경로를 이동하면 resources/app/runtime.json의 workspace를 수정하세요.\n프로젝트: ' + root + '\n');
console.log('Built:', output);
