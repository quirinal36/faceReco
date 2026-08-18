# Face Recognition System - Frontend

[한국어 문서](./README.kr.md)

Web dashboard frontend for the Face Recognition System.

## Tech Stack

- **React 19** - UI Library
- **Vite** - Build Tool & Dev Server
- **React Router v7** - Client-side Routing
- **Tailwind CSS** - Utility-first CSS Framework
- **Axios** - HTTP Client for API Communication
- **i18next** - Internationalization (i18n) Framework
- **Playwright** - End-to-End Testing

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Backend server running on loopback at `http://127.0.0.1:8000` with operator
  and device credentials provisioned as described in
  [Security & Privacy Operations](../docs/SECURITY.md)

### 1. Install Dependencies

```bash
npm install
```

### 2. API and authentication configuration

Local development uses Vite's same-origin `/api` proxy; no frontend environment
file is required. If a separately hosted UI needs `VITE_API_URL`, it may contain
only the public API origin. Never put an operator/device token in a `VITE_*`
variable because Vite exposes those values to the browser bundle.

At runtime the UI asks for one bearer credential, validates its role with
`/api/auth/whoami`, and keeps it in the current tab's session storage. It is
cleared when the tab closes or the API returns `401`. Never put the token in a
URL or query parameter.

### 3. Run Development Server

```bash
npm run dev
```

Open [https://127.0.0.1:5173](https://127.0.0.1:5173) and accept the local
development certificate if necessary. Vite and the backend both bind to
loopback; do not publish either service to the internet.

## Features

### Dashboard (`/`)
- **Real-time Camera Monitoring** - Live video stream from backend
- **Face Detection & Recognition** - Displays detected faces with bounding boxes
- **Statistics Display**
  - Detected faces count
  - Recognized faces count
  - FPS (Frames Per Second)

### Face Registration (`/register`)
- **Camera Capture** - Take photos using webcam
- **Face Upload** - Register new faces with names
- **Duplicate Detection** - Prevents duplicate registrations

### Face List (`/faces`)
- **View All Faces** - Browse all registered faces
- **Face Management** - Delete faces from database
- **Merge Duplicates** - Combine duplicate entries

## Available Scripts

### Development

```bash
# Start development server with hot reload
npm run dev

# Run ESLint for code quality
npm run lint

# Build for production
npm run build

# Preview production build
npm run preview
```

### Testing

```bash
# Run all Playwright E2E tests
npm test

# Run tests with UI mode
npm run test:ui

# Run tests in headed mode (visible browser)
npm run test:headed

# Debug tests
npm run test:debug

# View test report
npm run test:report
```

### Screenshots

```bash
# Capture deterministic synthetic screenshots only
FACERECO_SYNTHETIC_DOCS=1 npm run capture-screenshots
```

The capture script refuses to run without the synthetic-data flag and intercepts
all API calls. Never capture documentation from a live face or attendance store.

## Project Structure

```
frontend/
├── src/
│   ├── components/          # Reusable UI components
│   │   ├── Header.jsx       # Navigation header
│   │   ├── Sidebar.jsx      # Side navigation
│   │   ├── Layout.jsx       # Main layout wrapper
│   │   └── LanguageSwitcher.jsx  # Language toggle
│   ├── pages/               # Page components
│   │   ├── Dashboard.jsx    # Real-time monitoring
│   │   ├── FaceRegistration.jsx  # Face registration
│   │   └── FaceList.jsx     # Face management
│   ├── services/            # API services
│   │   └── api.js           # Axios API client
│   ├── i18n/                # Internationalization
│   │   ├── i18n.js          # i18n configuration
│   │   ├── en.json          # English translations
│   │   └── kr.json          # Korean translations
│   ├── main.jsx             # Application entry point
│   └── index.css            # Global styles
├── tests/                   # Playwright E2E tests
│   ├── face-registration.spec.js
│   └── playwright.config.js
├── capture-screenshots.js   # Screenshot capture script
├── package.json
├── vite.config.js
└── tailwind.config.js
```

## API Integration

The frontend communicates with the backend API through Axios. Base URL is configured via environment variable.

### API Endpoints Used

- `GET /api/camera/stream` - Real-time video stream (MJPEG)
- `GET /api/camera/stats` - Real-time statistics
- `POST /api/face/register` - Register new face
- `GET /api/faces/list` - List all registered faces
- `DELETE /api/face/{id}` - Delete face by ID
- `POST /api/faces/merge` - Merge duplicate faces (name in the JSON body)

See [API Guide](../API_GUIDE_EN.md) for detailed API documentation.

## Internationalization (i18n)

The application supports multiple languages using i18next:

- English (en)
- Korean (kr)

Language can be switched using the language toggle in the header.

### Adding New Languages

1. Create a new translation file in `src/i18n/` (e.g., `ja.json`)
2. Add translations for all keys
3. Import and register in `src/i18n/i18n.js`
4. Update the language switcher component

## Production Build

Build the application for production:

```bash
npm run build
```

The optimized files will be generated in the `dist/` directory.

### Deployment

Preview the built files only on loopback:

```bash
# Preview production build locally
npm run preview
```

For deployment, use the approved same-origin loopback/TLS service and host
firewall from the security guide. Do not launch an arbitrary public static
server or expose the Vite API proxy.

## Testing

End-to-end tests are written with Playwright and include:

- Face registration flow
- Camera stream display
- Face list management
- API error handling
- Mock webcam for testing without hardware

Run tests:

```bash
# All tests
npm test

# With UI
npm run test:ui

# Specific test file
npx playwright test tests/face-registration.spec.js
```

## Browser Compatibility

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

Webcam access requires HTTPS in production (except localhost).

## Troubleshooting

### Camera Access Issues

If the camera doesn't work:
- Check browser permissions
- Ensure HTTPS (required for production)
- Try different browsers
- Verify backend server is running

### CORS Errors

If API calls fail:
- Verify backend CORS configuration
- If used, verify that `VITE_API_URL` contains only the API origin and no token
- Ensure backend server is running

### Build Errors

```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

## Contributing

1. Follow React best practices
2. Use functional components with hooks
3. Write tests for new features
4. Run linter before committing

## License

TBD

---

Last Updated: 2026-02-09
