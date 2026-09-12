const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');

function startLocalServer(frontendDir, backendPort = 8000) {
  const types = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml', '.png': 'image/png', '.ico': 'image/x-icon' };
  const server = http.createServer((req, res) => {
    const pathname = new URL(req.url, 'http://localhost').pathname;
    if (/^\/(api|data)(\/|$)/.test(pathname)) {
      const upstream = http.request({ hostname: '127.0.0.1', port: backendPort,
        path: req.url, method: req.method, headers: { ...req.headers, host: `127.0.0.1:${backendPort}` } }, response => {
        res.writeHead(response.statusCode, response.headers);
        response.pipe(res);
      });
      upstream.on('error', () => { if (!res.headersSent) res.writeHead(502); res.end('Backend unavailable'); });
      res.on('close', () => upstream.destroy());
      req.pipe(upstream);
      return;
    }
    let decoded;
    try { decoded = decodeURIComponent(pathname); } catch { res.writeHead(400); res.end(); return; }
    let file = path.resolve(frontendDir, '.' + decoded);
    if (!file.startsWith(frontendDir + path.sep) && file !== frontendDir) {
      res.writeHead(403); res.end(); return;
    }
    if (!fs.existsSync(file) || fs.statSync(file).isDirectory()) file = path.join(frontendDir, 'index.html');
    res.setHeader('Content-Type', types[path.extname(file)] || 'application/octet-stream');
    const stream = fs.createReadStream(file);
    stream.on('error', () => { if (!res.headersSent) res.writeHead(404); res.end(); });
    stream.pipe(res);
  });
  return new Promise(resolve => server.listen(0, '127.0.0.1', () => resolve(server)));
}
module.exports = { startLocalServer };
