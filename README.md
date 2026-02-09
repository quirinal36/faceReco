# Face Recognition System

Real-time face detection and recognition system

[한국어 문서](./README.kr.md)

## Project Overview
A system providing real-time face recognition through camera integration and a web-based dashboard.

## Key Features
- Real-time camera integration
- Face recognition using Hugging Face models
- Web-based monitoring dashboard
- Face registration and management
- Multi-sample face matching for improved accuracy
- Real-time statistics (detected faces, recognized faces, FPS)

## Tech Stack
- **Backend**: Python 3.9+, FastAPI, OpenCV
- **ML**: InsightFace (buffalo_l), PyTorch
- **Frontend**: React 19, Vite, Tailwind CSS, React Router
- **Testing**: Playwright E2E Testing
- **DevOps**: Git, GitHub

## Documentation
- [PRD (Product Requirements)](./PRD.md)
- [Project Plan](./PROJECT_PLAN.md)
- [Learning Workbook](./LEARNING_WORKBOOK.md) - Technical learning guide for project managers
- [API Guide](./API_GUIDE.md) - FastAPI server usage guide
- [Troubleshooting Guide](./TROUBLESHOOTING.md) - Installation and execution issues

## Project Structure
```
faceReco/
├── backend/                # Backend server
│   ├── app.py             # Main application
│   ├── models/            # ML model modules
│   │   ├── face_detection.py      # Haar Cascade face detection
│   │   ├── face_recognition.py    # InsightFace face recognition
│   │   └── face_database.py       # Face database management
│   ├── camera/            # Camera processing module
│   ├── api/               # API endpoints
│   ├── data/              # Face database
│   │   ├── face_database.json     # Metadata
│   │   ├── embeddings/            # Face embeddings (512-dim)
│   │   └── faces/                 # Face images
│   └── requirements.txt   # Python dependencies
├── frontend/              # Frontend (React + Vite)
│   ├── src/
│   │   ├── components/         # UI components
│   │   ├── pages/              # Pages (Dashboard, FaceRegistration, FaceList)
│   │   ├── services/           # API services
│   │   └── utils/              # Utilities
│   ├── tests/                  # Playwright E2E tests
│   └── package.json
├── docs/                  # Documentation
├── tests/                 # Test code
├── PRD.md                 # Product Requirements
├── PROJECT_PLAN.md        # Project Plan
└── README.md              # This file
```

## Project Status
Current Status: **Milestone 5 - Web Dashboard Development In Progress** 🚧

### Completed Tasks
**Milestone 1: Initial Project Setup** ✅
- [x] GitHub repository creation
- [x] Project directory structure setup
- [x] Python virtual environment configuration
- [x] Basic dependency package installation
- [x] Documentation (PRD, PROJECT_PLAN, README)

**Milestone 2: Camera Integration and Basic Face Detection** ✅
- [x] OpenCV camera handler implementation
- [x] Real-time video stream processing
- [x] Haar Cascade face detection implementation
- [x] Face region bounding box display
- [x] Unit test creation

**Milestone 3: ML Model Integration** ✅
- [x] InsightFace buffalo_l model selection
- [x] FaceRecognizer class implementation (face embedding extraction)
- [x] FaceDatabase class implementation (face database management)
- [x] Face registration feature implementation
- [x] Face recognition and matching feature implementation
- [x] Unit test creation

**Milestone 4: Backend API Development** ✅
- [x] FastAPI project initialization
- [x] API endpoint design and implementation
- [x] CORS configuration
- [x] Real-time video streaming API
- [x] Face registration/query/deletion API
- [x] API documentation (Swagger UI)
- [x] Real-time statistics API

**Milestone 5: Web Dashboard Development** 🚧
- [x] React + Vite frontend project initialization
- [x] Basic layout structure (Header, Sidebar, Layout)
- [x] Page components (Dashboard, FaceRegistration, FaceList)
- [x] API client setup (Axios)
- [x] Real-time camera monitoring with statistics
- [x] Face registration page with camera capture
- [x] Face list management with duplicate detection
- [x] Playwright E2E testing setup
- [ ] Comprehensive testing and optimization

### Next Steps
- [ ] Integration testing and performance optimization (Milestone 5)
- [ ] Deployment documentation and Docker containerization (Milestone 6)

## Getting Started

### Prerequisites
- Python 3.8 or higher
- Git
- Webcam (for camera features)
- Node.js 18+ (for frontend)

### Installation

1. **Clone Repository**
   ```bash
   git clone https://github.com/quirinal36/faceReco.git
   cd faceReco
   ```

2. **Create and Activate Python Virtual Environment**
   ```bash
   # Create virtual environment
   python3 -m venv venv

   # Activate virtual environment (Linux/Mac)
   source venv/bin/activate

   # Activate virtual environment (Windows)
   venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   cd backend

   # Option 1: Production environment (recommended)
   pip install -r requirements.txt

   # Option 2: Minimal install (for quick testing)
   pip install -r requirements-minimal.txt

   # Option 3: Development environment (for developers)
   pip install -r requirements-dev.txt
   ```

   **Requirements File Descriptions**:
   - `requirements.txt` - Production environment (full features)
   - `requirements-minimal.txt` - Minimal environment (fast install, limited features)
   - `requirements-dev.txt` - Development environment (includes testing, linting, documentation tools)

   **Important**: InsightFace installation issues may occur on Windows.
   - **Recommended Solution**: Refer to Solution 1 or 2 in [Troubleshooting Guide](./TROUBLESHOOTING.md)
   - Install Visual Studio Build Tools or use Conda environment

4. **Verify Installation**
   ```bash
   # Check installed packages
   python test_installation.py
   ```

   **Note**: On first run, InsightFace buffalo_l model will be downloaded automatically (~600MB)

### Running the Application

#### 🚀 Quick Start (Recommended)

**Method 1: Using npm scripts** (Most convenient)
```bash
# Install frontend dependencies (first time only)
npm run install-all

# Run backend + frontend simultaneously
npm run dev
```

**Method 2: Using run scripts**
```bash
# Windows
start-dev.bat

# Linux/Mac
./start-dev.sh
```

After server starts:
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

---

#### Individual Execution (Manual)

**Virtual environment activation required**:
```bash
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows
cd backend
```

#### 1. Face Registration (Add new faces)
```bash
python app.py --mode register --camera-id 0
```
- Spacebar: Capture face
- Enter name and press Enter
- q: Exit

#### 2. Face Recognition (Real-time recognition)
```bash
python app.py --mode face_recognition --camera-id 0
```
- Registered faces: Green box + name + confidence
- Unregistered faces: Red box + "Unknown"
- q: Exit

#### 3. Face Detection Demo (Haar Cascade)
```bash
python app.py --mode face_detection --camera-id 0
```

#### 4. Camera Test
```bash
python app.py --mode camera --camera-id 0
```

#### 5. API Server (FastAPI) 🆕
```bash
# Method 1: Using app.py
python app.py --mode server

# Method 2: Direct server.py execution
python server.py
```

After server starts:
- **API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/api/health

**API Endpoints**:
- `POST /api/face/register` - Register face
- `GET /api/faces/list` - List registered faces
- `DELETE /api/face/{id}` - Delete face
- `GET /api/camera/stream` - Real-time video streaming
- `GET /api/camera/stats` - Real-time statistics
- `POST /api/faces/merge/{name}` - Merge duplicate faces

For detailed usage, see [API Guide](./API_GUIDE.md).

#### 6. Individual Module Execution
```bash
# Test camera handler
python -m camera.camera_handler

# Face detection demo
python -m models.face_detection

# Face recognition module test
python -m models.face_recognition
```

**Notes**:
- Webcam access permission required
- Press 'q' to exit the program
- Camera access may be restricted in WSL environments

### Development Environment Setup

1. **Code Formatting**
   ```bash
   # Code formatting with Black
   black backend/
   ```

2. **Running Tests**
   ```bash
   # Backend tests with pytest
   pytest tests/

   # Frontend E2E tests with Playwright
   cd frontend
   npx playwright test
   ```

## Development Guide

### Development Workflow
1. Create or select an issue
2. Create new branch (`git checkout -b feature/issue-name`)
3. Write code and tests
4. Commit and push
5. Create Pull Request

### Coding Style
- Python: Follow PEP 8, use Black formatter
- Write docstrings for functions and classes
- Write test code (recommended)
- React: Use functional components with hooks

### Testing
- **Backend**: pytest for unit tests
- **Frontend**: Playwright for E2E tests
- Test coverage goal: >80%

## GitHub Issues and Milestones
Project progress can be tracked at [GitHub Issues](https://github.com/quirinal36/faceReco/issues).

### Milestones
- **Milestone 1**: Initial Project Setup ✅
- **Milestone 2**: Camera Integration and Basic Face Detection ✅
- **Milestone 3**: ML Model Integration ✅
- **Milestone 4**: Backend API Development ✅
- **Milestone 5**: Web Dashboard Development 🚧
- **Milestone 6**: Integration and Deployment Preparation

## Features

### Multi-Sample Face Recognition
- Register multiple photos of the same person for improved accuracy
- Automatic duplicate detection and merging
- Uses maximum similarity among all samples for recognition

### Real-time Statistics Dashboard
- Live face detection count
- Recognition success rate
- Processing speed (FPS)
- Updated every second

### Comprehensive Testing
- Playwright E2E tests for frontend
- Webcam mocking for testing without hardware
- API integration tests

## License
TBD

---
Last Updated: 2026-02-09
