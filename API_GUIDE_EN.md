# Face Recognition API Guide

The edge API is a local biometric-data service. It is not supported on the public
internet. See [Security & Privacy Operations](./docs/SECURITY.md) before enabling
anything beyond loopback development.

## Authentication and roles

Configure two different random credentials of at least 32 characters before
startup (`FACERECO_OPERATOR_TOKEN` / `FACERECO_DEVICE_TOKEN`, or their protected
`*_FILE` forms). Examples below assume the operator credential is already in the
shell as `FACERECO_OPERATOR_TOKEN`; they never show or print its value.

- `operator`: enrollment, face list and authenticated thumbnails, delete/merge,
  camera/stream, and attendance management.
- `device`: the single local device's liveness calls only.
- `GET /api/health`: the only unauthenticated API endpoint.
- `GET /api/auth/whoami`: validates either credential and returns its role.

Every protected request uses `Authorization: Bearer ...`. Never append a token to
a URL or query string. The browser UI asks for one token, validates its role, and
retains it only for the current tab session; there is no `VITE_*` token setting.

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
uvicorn server:app --host 127.0.0.1 --port 8000 --reload
```

Loopback is the default and required production listener. Never use `0.0.0.0` or
a public address. A development-only trusted LAN/VPN bind requires one explicit
private address plus the server's explicit opt-in; production edge interaction
with Edu Manager is outbound HTTPS only.

## 📡 Connection Information

- **API Server**: http://127.0.0.1:8000
- **API Documentation (development only)**: http://127.0.0.1:8000/docs
- **ReDoc (development only)**: http://127.0.0.1:8000/redoc

Production disables Swagger, ReDoc, and the OpenAPI document.

## 📚 API Endpoints

### 1. Health Check
Check system status

```http
GET /api/health
```

**Response Example:**
```json
{
  "status": "healthy"
}
```

---

### 2. Face Registration
Register a new face in the database

```http
POST /api/face/register
Authorization: Bearer <operator-token>
Content-Type: multipart/form-data
```

**Parameters:**
- `name` (string, required): Name of the person to register
- `file` (file, required): Face image file (JPEG, PNG), at most 5 MiB

The HTTP client must send `Content-Length` (cURL, browsers, and `requests` do so
for ordinary multipart files). Chunked uploads are rejected, and the complete
multipart body is bounded to keep raw frames out of OS temporary storage.

**cURL Example:**
```bash
curl -X POST "http://127.0.0.1:8000/api/face/register" \
  -H "Authorization: Bearer ${FACERECO_OPERATOR_TOKEN}" \
  -F "name=홍길동" \
  -F "file=@/path/to/photo.jpg"
```

**Python Example:**
```python
import requests
import os

url = "http://127.0.0.1:8000/api/face/register"
files = {"file": open("photo.jpg", "rb")}
data = {"name": "홍길동"}
headers = {"Authorization": f"Bearer {os.environ['FACERECO_OPERATOR_TOKEN']}"}

response = requests.post(url, headers=headers, files=files, data=data)
print(response.json())
```

**Response Example (Success):**
```json
{
  "success": true,
  "face_id": "person_5d388b09d4ae48df8a07fc362e438f10",
  "name": "홍길동",
  "message": "Face registration completed."
}
```

**Response Example (Failure - Face Detection Failed):**
```json
{
  "success": false,
  "face_id": null,
  "name": null,
  "message": "Exactly one face must be visible in the image."
}
```

---

### 3. Face List
Retrieve all registered face information

```http
GET /api/faces/list
Authorization: Bearer <operator-token>
```

**cURL Example:**
```bash
curl "http://127.0.0.1:8000/api/faces/list" \
  -H "Authorization: Bearer ${FACERECO_OPERATOR_TOKEN}"
```

**Response Example:**
```json
{
  "total": 3,
  "faces": [
    {
      "face_id": "person_5d388b09d4ae48df8a07fc362e438f10",
      "name": "홍길동",
      "registered_at": "2026-02-06T15:30:45.123456",
      "last_seen": "2026-02-06T16:20:10.654321",
      "recognition_count": 25,
      "thumbnail_url": "/api/faces/person_5d388b09d4ae48df8a07fc362e438f10/thumbnail",
      "sample_count": 2
    },
    {
      "face_id": "person_22faf885bc414675807ee29b3db0f327",
      "name": "김철수",
      "registered_at": "2026-02-06T14:05:30.789012",
      "last_seen": null,
      "recognition_count": 0,
      "thumbnail_url": null,
      "sample_count": 1
    }
  ]
}
```

`thumbnail_url` is an API route, never a storage path. It requires the same
operator header and returns a bounded, non-cacheable image. There is no `/data`
static route:

```bash
curl "http://127.0.0.1:8000/api/faces/person_5d388b09d4ae48df8a07fc362e438f10/thumbnail" \
  -H "Authorization: Bearer ${FACERECO_OPERATOR_TOKEN}" \
  --output thumbnail.jpg
```

---

### 4. Delete Face
Delete a registered face

```http
DELETE /api/face/{face_id}
Authorization: Bearer <operator-token>
```

**Parameters:**
- `face_id` (path parameter, required): Face ID to delete

**cURL Example:**
```bash
curl -X DELETE "http://127.0.0.1:8000/api/face/person_5d388b09d4ae48df8a07fc362e438f10" \
  -H "Authorization: Bearer ${FACERECO_OPERATOR_TOKEN}"
```

**Response Example (Success):**
```json
{
  "success": true,
  "face_id": "person_5d388b09d4ae48df8a07fc362e438f10",
  "message": "Face data was deleted."
}
```

**Response Example (Failure):**
```json
{
  "detail": "Face not found"
}
```

---

### 5. Real-time Video Streaming
Real-time face recognition video stream

```http
GET /api/camera/stream
Authorization: Bearer <operator-token>
```

**Authenticated connectivity check:**

```bash
curl --max-time 5 "http://127.0.0.1:8000/api/camera/stream" \
  -H "Authorization: Bearer ${FACERECO_OPERATOR_TOKEN}" \
  --output /dev/null
```

A plain HTML/React `<img src>` does not attach the bearer header. Use the
application's authenticated stream client. Never work around the header by
placing the token in the stream URL.

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
curl http://127.0.0.1:8000/api/health

# 2. Register face (using test image)
curl -X POST "http://127.0.0.1:8000/api/face/register" \
  -H "Authorization: Bearer ${FACERECO_OPERATOR_TOKEN}" \
  -F "name=테스트" \
  -F "file=@test_image.jpg"

# 3. Check face list
curl "http://127.0.0.1:8000/api/faces/list" \
  -H "Authorization: Bearer ${FACERECO_OPERATOR_TOKEN}"

# 4. Verify the token role
curl "http://127.0.0.1:8000/api/auth/whoami" \
  -H "Authorization: Bearer ${FACERECO_OPERATOR_TOKEN}"
```

### 2. Python Client Example

```python
import requests
import json
import os

# Server address
BASE_URL = "http://127.0.0.1:8000"
HEADERS = {"Authorization": f"Bearer {os.environ['FACERECO_OPERATOR_TOKEN']}"}

# 1. Health check
response = requests.get(f"{BASE_URL}/api/health")
print("헬스체크:", json.dumps(response.json(), indent=2, ensure_ascii=False))

# 2. Register face
with open("photo.jpg", "rb") as f:
    files = {"file": f}
    data = {"name": "홍길동"}
    response = requests.post(
        f"{BASE_URL}/api/face/register", headers=HEADERS, files=files, data=data
    )
    print("등록 결과:", json.dumps(response.json(), indent=2, ensure_ascii=False))

# 3. Retrieve face list
response = requests.get(f"{BASE_URL}/api/faces/list", headers=HEADERS)
faces = response.json()
print(f"등록된 얼굴 수: {faces['total']}")
for face in faces['faces']:
    print(f"  - {face['name']} (ID: {face['face_id']})")

# 4. Delete face
face_id = "person_5d388b09d4ae48df8a07fc362e438f10"
response = requests.delete(f"{BASE_URL}/api/face/{face_id}", headers=HEADERS)
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

### Issue: Model artifacts are missing
```
Solution:
- Do not open production edge internet access for an automatic download
- Provision and verify the approved model on a controlled staging/build host
- Copy the frozen bundle to FACERECO_MODEL_ROOT/models/buffalo_l/*.onnx (or the
  directory matching the approved FACERECO_MODEL_NAME)
```

### Issue: CORS error
```
Solution:
- Set FACERECO_CORS_ORIGINS to the exact UI origin (scheme, host, and port)
- Do not use a wildcard; localhost and 127.0.0.1 are different origins
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

### GPU Acceleration (Required)

This backend runs biometric inference only on the local CUDA GPU. CPU fallback
is rejected, so install an ONNX Runtime build that provides
`CUDAExecutionProvider` before starting the service:

```bash
pip uninstall onnxruntime
pip install onnxruntime-gpu
```

On ARM devices such as Jetson, use the NVIDIA ONNX Runtime build compatible
with the installed JetPack/CUDA version. `python backend/test_installation.py`
must report `CUDAExecutionProvider`.

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

- **Development-only API Documentation**: http://127.0.0.1:8000/docs
- **Security and privacy operations**: [docs/SECURITY.md](./docs/SECURITY.md)
- **GitHub Repository**: [Project Link]
- **Issue Reporting**: GitHub Issues

---

**Updated**: 2026-08-16
**Version**: 1.0.0
