# 얼굴 인식 API 가이드

## 🚀 서버 실행

### 방법 1: app.py 사용 (권장)
```bash
cd backend
python app.py --mode server
```

### 방법 2: server.py 직접 실행
```bash
cd backend
python server.py
```

### 방법 3: Uvicorn 직접 실행
```bash
cd backend
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

## 📡 접속 정보

- **API 서버**: http://localhost:8000
- **API 문서 (Swagger UI)**: http://localhost:8000/docs
- **API 문서 (ReDoc)**: http://localhost:8000/redoc

## 📚 API 엔드포인트

### 1. 헬스체크
시스템 상태 확인

```http
GET /api/health
```

**응답 예시:**
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

### 2. 얼굴 등록
새로운 얼굴을 데이터베이스에 등록

```http
POST /api/face/register
Content-Type: multipart/form-data
```

**파라미터:**
- `name` (string, required): 등록할 사람의 이름
- `file` (file, required): 얼굴 이미지 파일 (JPEG, PNG)

**cURL 예시:**
```bash
curl -X POST "http://localhost:8000/api/face/register" \
  -F "name=홍길동" \
  -F "file=@/path/to/photo.jpg"
```

**Python 예시:**
```python
import requests

url = "http://localhost:8000/api/face/register"
files = {"file": open("photo.jpg", "rb")}
data = {"name": "홍길동"}

response = requests.post(url, files=files, data=data)
print(response.json())
```

**응답 예시 (성공):**
```json
{
  "success": true,
  "face_id": "person_20260206_153045",
  "name": "홍길동",
  "message": "'홍길동' 얼굴이 성공적으로 등록되었습니다."
}
```

**응답 예시 (실패 - 얼굴 감지 실패):**
```json
{
  "success": false,
  "face_id": null,
  "name": null,
  "message": "이미지에서 얼굴을 감지할 수 없습니다. 다른 이미지를 시도해주세요."
}
```

---

### 3. 얼굴 목록 조회
등록된 모든 얼굴 정보 조회

```http
GET /api/faces/list
```

**cURL 예시:**
```bash
curl -X GET "http://localhost:8000/api/faces/list"
```

**응답 예시:**
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

### 4. 얼굴 삭제
등록된 얼굴 삭제

```http
DELETE /api/face/{face_id}
```

**파라미터:**
- `face_id` (path parameter, required): 삭제할 얼굴 ID

**cURL 예시:**
```bash
curl -X DELETE "http://localhost:8000/api/face/person_20260206_153045"
```

**응답 예시 (성공):**
```json
{
  "success": true,
  "face_id": "person_20260206_153045",
  "message": "얼굴 ID 'person_20260206_153045'가 성공적으로 삭제되었습니다."
}
```

**응답 예시 (실패):**
```json
{
  "detail": "얼굴 ID 'invalid_id'를 찾을 수 없습니다."
}
```

---

### 5. 실시간 비디오 스트리밍
실시간 얼굴 인식 비디오 스트림

```http
GET /api/camera/stream
```

**사용 방법:**

#### HTML에서 사용:
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

#### React에서 사용:
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

**특징:**
- MJPEG 형식으로 스트리밍
- 실시간 얼굴 감지 및 인식
- 등록된 얼굴: 녹색 박스 + 이름 + 신뢰도
- 미등록 얼굴: 빨간색 박스 + "Unknown"

---

## 🔧 테스트 시나리오

### 1. 기본 동작 테스트

```bash
# 1. 헬스체크
curl http://localhost:8000/api/health

# 2. 얼굴 등록 (테스트 이미지 사용)
curl -X POST "http://localhost:8000/api/face/register" \
  -F "name=테스트" \
  -F "file=@test_image.jpg"

# 3. 얼굴 목록 확인
curl http://localhost:8000/api/faces/list

# 4. 비디오 스트림 확인 (브라우저에서)
# http://localhost:8000/api/camera/stream
```

### 2. Python 클라이언트 예시

```python
import requests
import json

# 서버 주소
BASE_URL = "http://localhost:8000"

# 1. 헬스체크
response = requests.get(f"{BASE_URL}/api/health")
print("헬스체크:", json.dumps(response.json(), indent=2, ensure_ascii=False))

# 2. 얼굴 등록
with open("photo.jpg", "rb") as f:
    files = {"file": f}
    data = {"name": "홍길동"}
    response = requests.post(f"{BASE_URL}/api/face/register", files=files, data=data)
    print("등록 결과:", json.dumps(response.json(), indent=2, ensure_ascii=False))

# 3. 얼굴 목록 조회
response = requests.get(f"{BASE_URL}/api/faces/list")
faces = response.json()
print(f"등록된 얼굴 수: {faces['total']}")
for face in faces['faces']:
    print(f"  - {face['name']} (ID: {face['face_id']})")

# 4. 얼굴 삭제
face_id = "person_20260206_153045"
response = requests.delete(f"{BASE_URL}/api/face/{face_id}")
print("삭제 결과:", json.dumps(response.json(), indent=2, ensure_ascii=False))
```

---

## 🐛 트러블슈팅

### 문제: 카메라를 찾을 수 없음
```
해결방법:
- 카메라가 연결되어 있는지 확인
- 다른 프로그램에서 카메라를 사용 중인지 확인
- backend/api/routes.py의 camera_id를 변경 (기본값: 0)
```

### 문제: 모델 다운로드 오류
```
해결방법:
- 인터넷 연결 확인
- InsightFace 모델이 자동으로 다운로드됨 (~200MB)
- 첫 실행 시 시간이 걸릴 수 있음
```

### 문제: CORS 오류
```
해결방법:
- backend/server.py의 origins 리스트에 프론트엔드 URL 추가
- 브라우저 캐시 삭제 후 재시도
```

### 문제: 얼굴 인식 정확도 낮음
```
해결방법:
- 조명이 밝은 곳에서 촬영
- 정면 얼굴 사진 사용
- 고해상도 이미지 사용
- backend/models/face_database.py의 threshold 값 조정 (기본값: 0.5)
```

---

## 📊 성능 최적화

### GPU 가속 (선택사항)
CUDA가 설치된 시스템에서 GPU 가속 사용:

```bash
pip uninstall onnxruntime
pip install onnxruntime-gpu
```

### 임계값 조정
얼굴 인식 임계값 조정 (backend/models/face_database.py):

```python
# 더 엄격한 매칭 (false positive 감소)
database = FaceDatabase(threshold=0.6)

# 더 관대한 매칭 (false negative 감소)
database = FaceDatabase(threshold=0.4)
```

---

## 📝 추가 정보

- **자동 생성 API 문서**: http://localhost:8000/docs
- **GitHub 리포지토리**: [프로젝트 링크]
- **이슈 리포트**: GitHub Issues

---

**작성일**: 2026-02-06
**버전**: 1.0.0
