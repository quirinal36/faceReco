# Face Recognition API Guide

## 🚀 Starting the Server

### Method 1: Using app.py (Recommended)
```bash
cd backend
python app.py --mode server
```

### Method 2: Running server.py Directly
```bash
cd backend
python server.py
```

### Method 3: Running Uvicorn Directly
```bash
cd backend
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

## 📡 Connection Information

- **API Server**: http://localhost:8000
- **API Documentation (Swagger UI)**: http://localhost:8000/docs
- **API Documentation (ReDoc)**: http://localhost:8000/redoc

## 📚 API Endpoints

### 1. Health Check
Check system status

```http
GET /api/health
```

**Response Example:**
```json
{
  "status": "healthy",
  "model_info": {
    "model_name": "buffalo_l",
    "device": "cpu",
    "embedding_size": 512,
    "det_size": [640, 640]
  },
  "database_info": {
    "total_faces": 5,
    "total_recognitions": 120,
    "threshold": 0.5
  }
}
```

---

### 2. Face Registration
Register a new face in the database

```http
POST /api/face/register
Content-Type: multipart/form-data
```

**Parameters:**
- `name` (string, required): Name of the person to register
- `file` (file, required): Face image file (JPEG, PNG)

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/api/face/register" \
  -F "name=홍길동" \
  -F "file=@/path/to/photo.jpg"
```

**Python Example:**
```python
import requests

url = "http://localhost:8000/api/face/register"
files = {"file": open("photo.jpg", "rb")}
data = {"name": "홍길동"}

response = requests.post(url, files=files, data=data)
print(response.json())
```

**Response Example (Success):**
```json
{
  "success": true,
  "face_id": "person_20260206_153045",
  "name": "홍길동",
  "message": "'홍길동' 얼굴이 성공적으로 등록되었습니다."
}
```

**Response Example (Failure - Face Detection Failed):**
```json
{
  "success": false,
  "face_id": null,
  "name": null,
  "message": "이미지에서 얼굴을 감지할 수 없습니다. 다른 이미지를 시도해주세요."
}
```

---

### 3. Face List
Retrieve all registered face information

```http
GET /api/faces/list
```

**cURL Example:**
```bash
curl -X GET "http://localhost:8000/api/faces/list"
```

**Response Example:**
```json
{
  "total": 3,
  "faces": [
    {
      "face_id": "person_20260206_153045",
      "name": "홍길동",
      "registered_at": "2026-02-06T15:30:45.123456",
      "last_seen": "2026-02-06T16:20:10.654321",
      "recognition_count": 25,
      "image_path": "faces/person_20260206_153045.jpg"
    },
    {
      "face_id": "person_20260206_140530",
      "name": "김철수",
      "registered_at": "2026-02-06T14:05:30.789012",
      "last_seen": null,
      "recognition_count": 0,
      "image_path": "faces/person_20260206_140530.jpg"
    }
  ]
}
```

---

### 4. Delete Face
Delete a registered face

```http
DELETE /api/face/{face_id}
```

**Parameters:**
- `face_id` (path parameter, required): Face ID to delete

**cURL Example:**
```bash
curl -X DELETE "http://localhost:8000/api/face/person_20260206_153045"
```

**Response Example (Success):**
```json
{
  "success": true,
  "face_id": "person_20260206_153045",
  "message": "얼굴 ID 'person_20260206_153045'가 성공적으로 삭제되었습니다."
}
```

**Response Example (Failure):**
```json
{
  "detail": "얼굴 ID 'invalid_id'를 찾을 수 없습니다."
}
```

---

### 5. Real-time Video Streaming
Real-time face recognition video stream

```http
GET /api/camera/stream
```

**Usage:**

#### Using in HTML:
```html
<!DOCTYPE html>
<html>
<head>
    <title>얼굴 인식 스트리밍</title>
</head>
<body>
    <h1>실시간 얼굴 인식</h1>
    <img src="http://localhost:8000/api/camera/stream"
         alt="Video Stream"
         width="640"
         height="480">
</body>
</html>
```

#### Using in React:
```jsx
function VideoStream() {
  return (
    <div>
      <h1>실시간 얼굴 인식</h1>
      <img
        src="http://localhost:8000/api/camera/stream"
        alt="Video Stream"
        width={640}
        height={480}
      />
    </div>
  );
}
```

**Features:**
- Streaming in MJPEG format
- Real-time face detection and recognition
- Registered faces: Green box + name + confidence score
- Unregistered faces: Red box + "Unknown"

---

## 🔧 Test Scenarios

### 1. Basic Operation Test

```bash
# 1. Health check
curl http://localhost:8000/api/health

# 2. Register face (using test image)
curl -X POST "http://localhost:8000/api/face/register" \
  -F "name=테스트" \
  -F "file=@test_image.jpg"

# 3. Check face list
curl http://localhost:8000/api/faces/list

# 4. Check video stream (in browser)
# http://localhost:8000/api/camera/stream
```

### 2. Python Client Example

```python
import requests
import json

# Server address
BASE_URL = "http://localhost:8000"

# 1. Health check
response = requests.get(f"{BASE_URL}/api/health")
print("헬스체크:", json.dumps(response.json(), indent=2, ensure_ascii=False))

# 2. Register face
with open("photo.jpg", "rb") as f:
    files = {"file": f}
    data = {"name": "홍길동"}
    response = requests.post(f"{BASE_URL}/api/face/register", files=files, data=data)
    print("등록 결과:", json.dumps(response.json(), indent=2, ensure_ascii=False))

# 3. Retrieve face list
response = requests.get(f"{BASE_URL}/api/faces/list")
faces = response.json()
print(f"등록된 얼굴 수: {faces['total']}")
for face in faces['faces']:
    print(f"  - {face['name']} (ID: {face['face_id']})")

# 4. Delete face
face_id = "person_20260206_153045"
response = requests.delete(f"{BASE_URL}/api/face/{face_id}")
print("삭제 결과:", json.dumps(response.json(), indent=2, ensure_ascii=False))
```

---

## 🐛 Troubleshooting

### Issue: Camera not found
```
Solution:
- Check if the camera is connected
- Check if another program is using the camera
- Change camera_id in backend/api/routes.py (default: 0)
```

### Issue: Model download error
```
Solution:
- Check internet connection
- InsightFace model downloads automatically (~200MB)
- First run may take some time
```

### Issue: CORS error
```
Solution:
- Add frontend URL to origins list in backend/server.py
- Clear browser cache and retry
```

### Issue: Low face recognition accuracy
```
Solution:
- Shoot in a well-lit location
- Use frontal face photos
- Use high-resolution images
- Adjust threshold value in backend/models/face_database.py (default: 0.5)
```

---

## 📊 Performance Optimization

### GPU Acceleration (Optional)
Use GPU acceleration on systems with CUDA installed:

```bash
pip uninstall onnxruntime
pip install onnxruntime-gpu
```

### Threshold Adjustment
Adjust face recognition threshold (backend/models/face_database.py):

```python
# Stricter matching (reduce false positives)
database = FaceDatabase(threshold=0.6)

# More lenient matching (reduce false negatives)
database = FaceDatabase(threshold=0.4)
```

---

## 📝 Additional Information

- **Auto-generated API Documentation**: http://localhost:8000/docs
- **GitHub Repository**: [Project Link]
- **Issue Reporting**: GitHub Issues

---

**Written**: 2026-02-06
**Version**: 1.0.0
