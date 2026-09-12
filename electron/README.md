# Local Electron app

Run `npm run build:electron`, then launch `dist/FaceReco-linux-arm64/FaceReco.sh`
(on another architecture the directory suffix follows `process.arch`).

The app bundles the production frontend and the installed Electron runtime.
It serves the UI on a loopback-only ephemeral port and proxies `/api` and `/data`
to the local face-recognition backend. No Vite server or HTTPS certificate is needed.

This is a build for this workstation, not a standalone distribution for another PC.
`resources/app/runtime.json` records the project directory. Keep that directory,
`.venv311`, and the downloaded InsightFace models in place. Registered faces and
attendance continue to use `backend/data`.

If a matching backend is already running on port 8000, the app reuses it and leaves
it running when closed. Otherwise it starts the backend with the project's Python
and stops that child process on exit. Backend logs are written to `backend.log`
in Electron's user-data directory. `--demo` explicitly selects camera-only demo mode.

The launcher uses the existing project's `--no-sandbox` runtime option for this
Linux setup; renderer Node integration is disabled and media access is restricted
to the app's local origin.
