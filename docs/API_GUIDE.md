# 얼굴 인식 API 가이드

Edge API는 로컬 생체정보 서비스이며 공개 인터넷 배포를 지원하지 않습니다.
Loopback을 벗어나는 개발 설정 전에 [보안 및 개인정보 운영 가이드](./SECURITY.md)를
확인하세요.

## 인증과 역할

시작 전에 서로 다른 32자 이상의 무작위 인증정보 두 개를
`FACERECO_OPERATOR_TOKEN` / `FACERECO_DEVICE_TOKEN` 또는 보호된 각
`*_FILE` 설정으로 준비합니다. 아래 예시는 operator 인증정보가 shell의
`FACERECO_OPERATOR_TOKEN`에 이미 있고 값을 출력하지 않는다고 가정합니다.

- `operator`: 얼굴 등록·목록·인증 썸네일·삭제/통합, camera/stream, 출석 관리
- `device`: 단일 로컬 device의 liveness 호출만 허용
- `GET /api/health`: 유일한 무인증 API
- `GET /api/auth/whoami`: 두 역할의 인증정보를 확인하고 역할만 반환

보호된 모든 요청은 `Authorization: Bearer ...` header를 사용합니다. Token을
URL이나 query string에 추가하지 마세요. Browser UI는 token 하나를 입력받아
역할을 확인하고 현재 tab session 동안만 보관하며 `VITE_*` token 설정은
사용하지 않습니다.

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
uvicorn server:app --host 127.0.0.1 --port 8000 --reload
```

Loopback은 기본값이며 운영 환경에서 필수입니다. `0.0.0.0`이나 public 주소를
사용하지 마세요. 개발 전용의 신뢰된 LAN/VPN은 특정 private 주소와 명시적
opt-in이 모두 필요하며, 운영 edge와 Edu Manager의 연동은 outbound HTTPS만
사용합니다.

## 📡 접속 정보

- **API 서버**: http://127.0.0.1:8000
- **API 문서(개발 모드 전용)**: http://127.0.0.1:8000/docs
- **ReDoc(개발 모드 전용)**: http://127.0.0.1:8000/redoc

운영 모드에서는 Swagger, ReDoc, OpenAPI 문서를 비활성화합니다.

## 📚 API 엔드포인트

### 1. 헬스체크
시스템 상태 확인

```http
GET /api/health
```

**응답 예시:**
```json
{
  "status": "healthy"
}
```

---

### 2. 얼굴 등록
새로운 얼굴을 데이터베이스에 등록

```http
POST /api/face/register
Authorization: Bearer <operator-token>
Content-Type: multipart/form-data
```

**파라미터:**
- `name` (string, required): 등록할 사람의 이름
- `file` (file, required): 얼굴 이미지 파일 (JPEG, PNG), 최대 5 MiB

HTTP 클라이언트는 `Content-Length`를 보내야 합니다(일반 multipart 파일을
전송하는 cURL, 브라우저, `requests`는 자동으로 설정합니다). Chunked upload는
거부하며, 원본 frame이 OS 임시 저장소에 기록되지 않도록 전체 multipart body도
제한합니다.

**cURL 예시:**
```bash
curl -X POST "http://127.0.0.1:8000/api/face/register" \
  -H "Authorization: Bearer ${FACERECO_OPERATOR_TOKEN}" \
  -F "name=홍길동" \
  -F "file=@/path/to/photo.jpg"
```

**Python 예시:**
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

**응답 예시 (성공):**
```json
{
  "success": true,
  "face_id": "person_5d388b09d4ae48df8a07fc362e438f10",
  "name": "홍길동",
  "message": "Face registration completed."
}
```

**응답 예시 (실패 - 얼굴 감지 실패):**
```json
{
  "success": false,
  "face_id": null,
  "name": null,
  "message": "Exactly one face must be visible in the image."
}
```

---

### 3. 얼굴 목록 조회
등록된 모든 얼굴 정보 조회

```http
GET /api/faces/list
Authorization: Bearer <operator-token>
```

**cURL 예시:**
```bash
curl "http://127.0.0.1:8000/api/faces/list" \
  -H "Authorization: Bearer ${FACERECO_OPERATOR_TOKEN}"
```

**응답 예시:**
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

`thumbnail_url`은 저장소 경로가 아닌 API route입니다. 동일한 operator header가
필요하고 제한된 크기의 cache 금지 이미지를 반환합니다. `/data` 정적 route는
없습니다.

```bash
curl "http://127.0.0.1:8000/api/faces/person_5d388b09d4ae48df8a07fc362e438f10/thumbnail" \
  -H "Authorization: Bearer ${FACERECO_OPERATOR_TOKEN}" \
  --output thumbnail.jpg
```

---

### 4. 얼굴 삭제
등록된 얼굴 삭제

```http
DELETE /api/face/{face_id}
Authorization: Bearer <operator-token>
```

**파라미터:**
- `face_id` (path parameter, required): 삭제할 얼굴 ID

**cURL 예시:**
```bash
curl -X DELETE "http://127.0.0.1:8000/api/face/person_5d388b09d4ae48df8a07fc362e438f10" \
  -H "Authorization: Bearer ${FACERECO_OPERATOR_TOKEN}"
```

**응답 예시 (성공):**
```json
{
  "success": true,
  "face_id": "person_5d388b09d4ae48df8a07fc362e438f10",
  "message": "Face data was deleted."
}
```

**응답 예시 (실패):**
```json
{
  "detail": "Face not found"
}
```

---

### 5. 실시간 비디오 스트리밍
실시간 얼굴 인식 비디오 스트림

```http
GET /api/camera/stream
Authorization: Bearer <operator-token>
```

**인증 연결 확인:**

```bash
curl --max-time 5 "http://127.0.0.1:8000/api/camera/stream" \
  -H "Authorization: Bearer ${FACERECO_OPERATOR_TOKEN}" \
  --output /dev/null
```

일반 HTML/React `<img src>`는 Bearer header를 추가하지 못합니다. 애플리케이션의
인증 stream client를 사용하고 token을 stream URL에 넣어 우회하지 마세요.

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
curl http://127.0.0.1:8000/api/health

# 2. 얼굴 등록 (테스트 이미지 사용)
curl -X POST "http://127.0.0.1:8000/api/face/register" \
  -H "Authorization: Bearer ${FACERECO_OPERATOR_TOKEN}" \
  -F "name=테스트" \
  -F "file=@test_image.jpg"

# 3. 얼굴 목록 확인
curl "http://127.0.0.1:8000/api/faces/list" \
  -H "Authorization: Bearer ${FACERECO_OPERATOR_TOKEN}"

# 4. Token 역할 확인
curl "http://127.0.0.1:8000/api/auth/whoami" \
  -H "Authorization: Bearer ${FACERECO_OPERATOR_TOKEN}"
```

### 2. Python 클라이언트 예시

```python
import requests
import json
import os

# 서버 주소
BASE_URL = "http://127.0.0.1:8000"
HEADERS = {"Authorization": f"Bearer {os.environ['FACERECO_OPERATOR_TOKEN']}"}

# 1. 헬스체크
response = requests.get(f"{BASE_URL}/api/health")
print("헬스체크:", json.dumps(response.json(), indent=2, ensure_ascii=False))

# 2. 얼굴 등록
with open("photo.jpg", "rb") as f:
    files = {"file": f}
    data = {"name": "홍길동"}
    response = requests.post(
        f"{BASE_URL}/api/face/register", headers=HEADERS, files=files, data=data
    )
    print("등록 결과:", json.dumps(response.json(), indent=2, ensure_ascii=False))

# 3. 얼굴 목록 조회
response = requests.get(f"{BASE_URL}/api/faces/list", headers=HEADERS)
faces = response.json()
print(f"등록된 얼굴 수: {faces['total']}")
for face in faces['faces']:
    print(f"  - {face['name']} (ID: {face['face_id']})")

# 4. 얼굴 삭제
face_id = "person_5d388b09d4ae48df8a07fc362e438f10"
response = requests.delete(f"{BASE_URL}/api/face/{face_id}", headers=HEADERS)
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

### 문제: 모델 artifact가 없음
```
해결방법:
- 자동 다운로드를 위해 운영 edge의 인터넷 접근을 열지 않기
- 통제된 staging/build 호스트에서 승인된 모델을 준비하고 검증하기
- 고정된 bundle을 FACERECO_MODEL_ROOT/models/buffalo_l/*.onnx(또는 승인된
  FACERECO_MODEL_NAME과 일치하는 디렉터리)에 복사하기
```

### 문제: CORS 오류
```
해결방법:
- FACERECO_CORS_ORIGINS에 UI의 정확한 origin(scheme, host, port) 설정
- wildcard를 사용하지 않기; localhost와 127.0.0.1은 서로 다른 origin임
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

### GPU 가속 (필수)

이 백엔드는 로컬 CUDA GPU로만 얼굴 인식을 실행합니다. CPU fallback은 허용되지
않으며, 시작 전 `CUDAExecutionProvider`를 제공하는 ONNX Runtime을 설치해야 합니다.

```bash
pip uninstall onnxruntime
pip install onnxruntime-gpu
```

Jetson 등 ARM 장비에서는 해당 JetPack/CUDA 버전에 맞는 NVIDIA 제공 ONNX Runtime
빌드를 사용하세요. 설치 후 `python backend/test_installation.py`에서
`CUDAExecutionProvider`가 표시되어야 합니다.

이 저장소의 배포 장비에서 직접 빌드한 wheel이 있다면, PyPI 패키지 대신 그 wheel을
설치합니다.

```bash
python -m pip install /tmp/onnxruntime/build/Linux/Release/dist/onnxruntime_gpu-1.30.0-cp312-cp312-linux_aarch64.whl
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

- **개발 모드 전용 API 문서**: http://127.0.0.1:8000/docs
- **보안 및 개인정보 운영**: [SECURITY.md](./SECURITY.md)
- **GitHub 리포지토리**: [프로젝트 링크]
- **이슈 리포트**: GitHub Issues

---

**업데이트**: 2026-08-16
**버전**: 1.0.0
