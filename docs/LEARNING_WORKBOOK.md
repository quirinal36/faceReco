# 얼굴 인식 프로젝트 학습 워크북 (Learning Workbook)
**프로젝트 관리자를 위한 제1원칙 기반 학습 가이드**

> "복잡한 것을 가장 기본적인 진리로 분해하고, 그로부터 추론해 나가라" - 제1원칙 사고방식

---

## 📚 목차
1. [학습 워크북 사용 방법](#학습-워크북-사용-방법)
2. [제1원칙으로 분해하기](#제1원칙으로-분해하기)
3. [Level 1: 기초 개념](#level-1-기초-개념)
4. [Level 2: 핵심 기술 스택](#level-2-핵심-기술-스택)
5. [Level 3: 시스템 통합](#level-3-시스템-통합)
6. [Level 4: 프로젝트 관리](#level-4-프로젝트-관리)
7. [실전 체크리스트](#실전-체크리스트)
8. [문제 해결 가이드](#문제-해결-가이드)

---

## 학습 워크북 사용 방법

### 워크북의 목적
이 워크북은 **AI가 코드를 작성하더라도, 프로젝트 관리자로서 반드시 이해해야 할 핵심 개념**을 정리한 문서입니다.

### 학습 원칙
1. **WHY(왜) → WHAT(무엇) → HOW(어떻게)** 순서로 학습
2. **복잡한 개념을 가장 단순한 요소로 분해**하여 이해
3. **각 기술이 왜 필요한지** 먼저 이해한 후 학습
4. **실제 프로젝트 코드와 연결**하여 학습

### 체크 방법
- [ ] 각 섹션 완료 시 체크박스 표시
- [ ] 이해되지 않는 부분은 `❓` 표시 후 질문 정리
- [ ] 실제 코드를 확인하며 학습한 내용은 `✅` 표시

---

## 제1원칙으로 분해하기

### 우리가 만들고 있는 것: "얼굴 인식 시스템"

#### 가장 기본적인 질문들
```
Q1: 얼굴 인식은 왜 가능한가?
└─> 얼굴은 고유한 패턴을 가지고 있다
    └─> 이 패턴을 숫자로 표현할 수 있다 (벡터/임베딩)
        └─> 숫자를 비교하여 같은 사람인지 판단할 수 있다

Q2: 컴퓨터는 어떻게 이미지를 "본다"는 건가?
└─> 이미지는 숫자의 배열(픽셀)이다
    └─> 각 픽셀은 색상 값을 가진다 (RGB: 0-255)
        └─> 컴퓨터는 이 숫자 패턴을 분석한다

Q3: 카메라에서 웹 브라우저까지 어떻게 전달되는가?
└─> 카메라 → 바이트 스트림 → 서버 처리 → HTTP 응답 → 브라우저 렌더링
```

### 프로젝트를 3가지 핵심 구성요소로 분해

```
┌─────────────────────────────────────────────────────────────┐
│                     얼굴 인식 시스템                         │
└─────────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
    ┌───▼───┐        ┌────▼────┐       ┌────▼────┐
    │입력부  │        │ 처리부  │       │ 출력부   │
    │(카메라)│        │ (AI)    │       │  (웹)   │
    └───────┘        └─────────┘       └─────────┘
        │                 │                 │
     OpenCV          Transformers        FastAPI
                       PyTorch             React
```

---

## Level 1: 기초 개념

> 이 레벨은 **기술을 배우기 전에 반드시 이해해야 할 기본 원리**입니다.

### 1.1 이미지의 본질 이해하기

#### 학습 목표
- [ ] 디지털 이미지가 어떻게 저장되는지 이해
- [ ] 픽셀과 해상도의 관계 이해
- [ ] 색상 공간(RGB, BGR, Grayscale)의 차이 이해

#### 핵심 개념

**이미지 = 숫자의 3차원 배열**
```python
# 예시: 640x480 컬러 이미지
# 형태: (높이, 너비, 채널) = (480, 640, 3)
#
# image[0][0] = [255, 0, 0]  # 빨간색 픽셀
#                 R   G  B
```

**왜 이것을 알아야 하는가?**
- OpenCV로 카메라에서 받은 이미지가 이런 형태이기 때문
- ML 모델에 입력할 때 이미지를 전처리해야 하기 때문
- 에러 디버깅 시 형태(shape) 문제가 자주 발생하기 때문

**실습 질문**
```
Q: 우리 프로젝트의 camera_handler.py에서 반환하는 이미지 크기는?
A: [실제 코드 확인 후 작성]

Q: BGR과 RGB의 차이는? OpenCV는 어떤 것을 사용?
A: [학습 후 작성]
```

#### 관련 파일
- [backend/camera/camera_handler.py](backend/camera/camera_handler.py)
- [backend/models/face_detection.py](backend/models/face_detection.py)

---

### 1.2 머신러닝의 본질 이해하기

#### 학습 목표
- [ ] 머신러닝이 "학습한다"는 것의 의미 이해
- [ ] 모델, 가중치, 추론의 개념 이해
- [ ] 전이 학습(Transfer Learning)의 원리 이해

#### 핵심 개념

**머신러닝 = 패턴을 찾는 수학 함수**
```
입력(이미지) → [모델] → 출력(얼굴 좌표, 임베딩 벡터)
                  ↑
              학습된 가중치
```

**우리는 모델을 어떻게 사용하는가?**
1. **사전 학습된 모델 다운로드** (Hugging Face에서)
   - 이미 수백만 장의 얼굴로 학습됨
   - 우리는 이 가중치를 그대로 사용 (전이 학습)

2. **추론(Inference)**만 수행
   - 학습 X (Training)
   - 예측만 O (Inference)

**왜 이것을 알아야 하는가?**
- Hugging Face에서 어떤 모델을 선택해야 하는지 판단하기 위해
- 모델의 입력/출력 형태를 이해하기 위해
- 성능 문제 발생 시 원인을 파악하기 위해

**실습 질문**
```
Q: 우리 프로젝트에서 사용할 Hugging Face 모델은?
A: [Milestone 3에서 결정 예정]

Q: 모델의 입력으로 어떤 형태의 데이터가 필요한가?
A: [모델 선정 후 작성]

Q: 얼굴 임베딩 벡터란 무엇인가?
A: [학습 후 작성]
```

#### 추천 학습 자료
- [ ] [머신러닝이란? (10분 개념 설명)](https://www.youtube.com/results?search_query=machine+learning+basics+korean)
- [ ] [전이 학습 개념](https://www.youtube.com/results?search_query=transfer+learning+explained)

---

### 1.3 웹의 작동 원리 이해하기

#### 학습 목표
- [ ] 클라이언트-서버 구조 이해
- [ ] HTTP 요청/응답의 흐름 이해
- [ ] REST API의 개념 이해

#### 핵심 개념

**웹 = 요청과 응답**
```
브라우저(클라이언트)  ←─HTTP─→  서버(Backend)
       │                           │
    사용자 인터페이스           비즈니스 로직
    (React/Vue.js)             (FastAPI/Python)
                                   │
                                카메라 + AI
```

**우리 프로젝트의 데이터 흐름**
```
1. 사용자가 "얼굴 인식 시작" 버튼 클릭
   └─> 브라우저가 서버에 요청: GET /api/camera/stream

2. 서버가 카메라에서 이미지 가져옴
   └─> OpenCV로 프레임 캡처

3. 서버가 AI 모델로 얼굴 인식
   └─> Transformers 모델로 얼굴 감지

4. 서버가 결과를 브라우저로 전송
   └─> HTTP 응답 (JSON 또는 이미지 스트림)

5. 브라우저가 화면에 표시
   └─> React/Vue.js로 렌더링
```

**왜 이것을 알아야 하는가?**
- API 설계 시 어떤 엔드포인트가 필요한지 결정하기 위해
- 프론트엔드-백엔드 간 데이터 형식을 정의하기 위해
- 에러 발생 시 어디서 문제가 생겼는지 추적하기 위해

**실습 질문**
```
Q: 우리 프로젝트에서 필요한 API 엔드포인트는?
A: [PROJECT_PLAN.md Milestone 4 참조]
   - GET /api/camera/stream
   - POST /api/face/register
   - GET /api/face/recognize
   - 등

Q: 실시간 비디오 스트림은 어떻게 전송하는가?
A: [학습 후 작성 - WebSocket or Server-Sent Events]
```

---

## Level 2: 핵심 기술 스택

> 이 레벨은 **프로젝트에서 사용하는 각 기술을 심도 있게 학습**합니다.

### 2.1 Python 기초

#### 학습 목표
- [ ] Python 가상환경의 필요성 이해
- [ ] pip와 requirements.txt 사용법
- [ ] Python 모듈과 패키지 구조 이해
- [ ] 객체지향 프로그래밍 기초 (클래스, 메서드)

#### 왜 이것을 알아야 하는가?
- 의존성 관리 문제 해결을 위해
- 프로젝트 구조를 이해하기 위해
- 코드 리뷰 시 기본적인 문법을 이해하기 위해

#### 핵심 개념

**가상환경 (venv)**
```bash
# 왜 가상환경이 필요한가?
# → 프로젝트마다 다른 버전의 패키지를 사용할 수 있게 격리

python3 -m venv venv          # 가상환경 생성
source venv/bin/activate      # 활성화
pip install -r requirements.txt  # 패키지 설치
```

**프로젝트 구조**
```
backend/
├── __init__.py        # 이 디렉토리를 Python 패키지로 만듦
├── app.py             # 진입점 (Entry Point)
├── models/            # 모델 관련 모듈
│   ├── __init__.py
│   └── face_detection.py
└── camera/            # 카메라 관련 모듈
    ├── __init__.py
    └── camera_handler.py
```

**관리자가 알아야 할 Python 명령어**
```bash
# 패키지 설치
pip install opencv-python

# 설치된 패키지 목록 저장
pip freeze > requirements.txt

# 특정 패키지 버전 확인
pip show opencv-python

# 패키지 업그레이드
pip install --upgrade transformers
```

#### 실습 과제
- [ ] 현재 설치된 패키지 목록 확인
- [ ] requirements.txt 파일 읽고 각 패키지의 역할 이해
- [ ] 가상환경 활성화/비활성화 연습

#### 관련 파일
- [backend/requirements.txt](backend/requirements.txt)
- [venv/](venv/)

---

### 2.2 OpenCV - 카메라 및 이미지 처리

#### 학습 목표
- [ ] OpenCV가 무엇인지, 왜 사용하는지 이해
- [ ] 카메라 캡처의 원리 이해
- [ ] 이미지 전처리의 필요성 이해
- [ ] Haar Cascade 얼굴 감지 원리 이해

#### 왜 이것을 알아야 하는가?
- 카메라 연동 문제 해결을 위해
- 성능 최적화 결정을 내리기 위해
- 얼굴 감지 정확도 문제 디버깅을 위해

#### 핵심 개념

**OpenCV = Open Source Computer Vision Library**
- 이미지/비디오 처리를 위한 라이브러리
- C++로 작성되어 빠름
- Python 바인딩 제공

**카메라 캡처 흐름**
```python
import cv2

# 1. 카메라 객체 생성
cap = cv2.VideoCapture(0)  # 0 = 기본 카메라

# 2. 루프로 프레임 읽기
while True:
    ret, frame = cap.read()  # ret = 성공 여부, frame = 이미지 배열

    if not ret:
        break  # 프레임 읽기 실패

    # 3. 프레임 처리 (얼굴 감지 등)
    # ...

    # 4. 화면에 표시
    cv2.imshow('Camera', frame)

    # 5. 'q' 키 누르면 종료
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# 6. 리소스 해제
cap.release()
cv2.destroyAllWindows()
```

**Haar Cascade 얼굴 감지**
- 사전 학습된 XML 파일 사용
- 빠르지만 정확도는 중간
- 실시간 처리에 적합

```python
# 얼굴 감지기 로드
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
)

# 얼굴 감지
faces = face_cascade.detectMultiScale(
    gray_image,      # 그레이스케일 이미지
    scaleFactor=1.1, # 이미지 크기 축소 비율
    minNeighbors=5,  # 얼굴로 인정하기 위한 최소 이웃 수
    minSize=(30, 30) # 최소 얼굴 크기
)

# faces = [(x, y, w, h), ...] 형태의 배열
```

**프로젝트에서 사용하는 부분**
1. [camera_handler.py](backend/camera/camera_handler.py) - 카메라 캡처
2. [face_detection.py](backend/models/face_detection.py) - 얼굴 감지

#### 관리자가 알아야 할 질문들

```
Q: 카메라가 열리지 않을 때 확인할 것은?
A:
   1. 다른 프로그램이 카메라를 사용 중인가?
   2. WSL 환경인가? (WSL은 카메라 접근 제한)
   3. 카메라 ID가 올바른가? (0, 1, 2 등)

Q: FPS(Frames Per Second)가 낮을 때 원인은?
A:
   1. 카메라 해상도가 너무 높은가?
   2. AI 모델 추론 시간이 오래 걸리는가?
   3. CPU/GPU 리소스가 부족한가?

Q: Haar Cascade vs MTCNN vs CNN 기반 모델?
A:
   - Haar Cascade: 가장 빠름, 정확도 낮음
   - MTCNN: 중간 속도, 중간 정확도
   - CNN (딥러닝): 느림, 정확도 높음
   → 실시간 처리는 Haar, 높은 정확도는 딥러닝
```

#### 실습 과제
- [ ] camera_handler.py 코드 읽고 각 함수의 역할 이해
- [ ] 직접 카메라 테스트 실행해보기
- [ ] 얼굴 감지 파라미터 조정해보기 (scaleFactor, minNeighbors)

#### 추천 학습 자료
- [ ] [OpenCV 공식 튜토리얼](https://docs.opencv.org/4.x/d6/d00/tutorial_py_root.html)
- [ ] [얼굴 감지 원리 설명](https://www.youtube.com/results?search_query=haar+cascade+face+detection)

---

### 2.3 Transformers & PyTorch - 머신러닝 모델

#### 학습 목표
- [ ] Hugging Face Transformers 라이브러리 이해
- [ ] PyTorch 기본 개념 이해
- [ ] 모델 로드 및 추론 방법 이해
- [ ] 얼굴 임베딩(Face Embedding) 개념 이해

#### 왜 이것을 알아야 하는가?
- Milestone 3에서 모델 선정 시 의사결정을 위해
- 모델 성능 문제 해결을 위해
- 메모리/속도 최적화 결정을 내리기 위해

#### 핵심 개념

**Hugging Face = ML 모델의 GitHub**
- 사전 학습된 모델들이 공유되는 플랫폼
- transformers 라이브러리로 쉽게 사용 가능
- 모델 카드(Model Card)에 사용법과 성능 정보 제공

**얼굴 인식 모델의 흐름**
```
입력 이미지 → 전처리 → 모델 추론 → 후처리 → 결과
(640x480)    (정규화)  (임베딩 추출)  (비교)   (동일인 여부)
```

**얼굴 임베딩 (Face Embedding)**
```python
# 얼굴 이미지를 512차원 벡터로 변환
# 예시: [0.2, -0.5, 0.8, ..., 0.1]  # 512개의 숫자

# 두 얼굴의 유사도 계산
similarity = cosine_similarity(embedding1, embedding2)

# 임계값으로 동일인 판단
if similarity > 0.6:  # 임계값
    print("같은 사람입니다")
```

**프로젝트에서 사용 예정 (Milestone 3)**
```python
from transformers import pipeline

# 얼굴 인식 파이프라인 생성
face_recognizer = pipeline('image-classification', model='모델명')

# 얼굴 임베딩 추출
embedding = face_recognizer(image)

# 데이터베이스의 임베딩과 비교
# ...
```

#### 관리자가 알아야 할 질문들

```
Q: Hugging Face에서 얼굴 인식 모델 선정 기준은?
A:
   1. 모델 크기 (작을수록 빠름, 메모리 적게 사용)
   2. 정확도 (Accuracy)
   3. 추론 속도 (FPS)
   4. 최근 업데이트 여부
   5. 사용 사례(Use case)가 우리 프로젝트와 맞는가?

Q: 모델이 너무 느릴 때 해결 방법은?
A:
   1. 더 작은 모델로 변경
   2. GPU 사용 (CUDA)
   3. 모델 양자화 (Quantization)
   4. 배치 처리

Q: 모델 메모리 사용량을 확인하는 방법은?
A:
   - nvidia-smi (GPU)
   - htop/top (CPU)
   - Python: memory_profiler
```

#### Milestone 3 준비 사항
- [ ] Hugging Face에서 얼굴 인식 모델 조사
  - 추천: `deepface`, `arcface`, `facenet` 등
- [ ] 각 모델의 장단점 비교표 작성
- [ ] 테스트 이미지로 성능 측정

#### 추천 학습 자료
- [ ] [Hugging Face 모델 허브](https://huggingface.co/models?pipeline_tag=image-classification)
- [ ] [얼굴 인식 기술 설명](https://www.youtube.com/results?search_query=face+recognition+explained)
- [ ] [Face Embedding 개념](https://www.youtube.com/results?search_query=face+embedding)

---

### 2.4 FastAPI - 백엔드 API 개발

#### 학습 목표
- [ ] FastAPI가 무엇이고 왜 사용하는지 이해
- [ ] REST API 설계 원칙 이해
- [ ] API 엔드포인트 작성 방법 이해
- [ ] CORS 개념 이해

#### 왜 이것을 알아야 하는가?
- Milestone 4에서 API 설계 시 의사결정을 위해
- 프론트엔드-백엔드 인터페이스 정의를 위해
- API 에러 디버깅을 위해

#### 핵심 개념

**FastAPI = 빠르고 현대적인 Python 웹 프레임워크**
- 자동 문서화 (Swagger UI)
- 타입 힌팅 지원
- 비동기 처리 지원
- 빠른 성능

**기본 API 작성 예시**
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS 설정 (프론트엔드 접근 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 오리진 허용 (개발 시)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GET 엔드포인트
@app.get("/api/faces/list")
async def get_faces():
    """등록된 얼굴 목록 조회"""
    return {"faces": [...]}

# POST 엔드포인트
@app.post("/api/face/register")
async def register_face(name: str, image: bytes):
    """새로운 얼굴 등록"""
    # 얼굴 임베딩 추출
    # 데이터베이스 저장
    return {"status": "success", "id": 123}

# 서버 실행
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**우리 프로젝트의 API 설계 (Milestone 4)**
```
GET  /api/camera/stream     - 실시간 비디오 스트림
POST /api/face/register     - 얼굴 등록
GET  /api/face/recognize    - 얼굴 인식
GET  /api/faces/list        - 등록된 얼굴 목록
DELETE /api/face/{id}       - 얼굴 삭제
```

#### 관리자가 알아야 할 질문들

```
Q: REST API 설계 시 주의할 점은?
A:
   1. HTTP 메서드 올바르게 사용
      - GET: 조회
      - POST: 생성
      - PUT/PATCH: 수정
      - DELETE: 삭제
   2. 명사형 URL 사용 (/api/faces, /api/face/123)
   3. 버전 관리 (/api/v1/faces)
   4. 적절한 HTTP 상태 코드 (200, 201, 400, 404, 500)

Q: CORS 에러가 발생할 때 해결 방법은?
A:
   - FastAPI에 CORSMiddleware 추가
   - 프론트엔드 도메인을 allow_origins에 추가

Q: 비디오 스트림은 어떻게 전송하는가?
A:
   1. MJPEG 스트리밍 (간단, HTTP)
   2. WebSocket (양방향 통신)
   3. Server-Sent Events (단방향)
   → 우리 프로젝트에 적합한 방식 선택 필요
```

#### 실습 과제
- [ ] FastAPI 공식 튜토리얼 따라하기
- [ ] 간단한 API 엔드포인트 작성해보기
- [ ] Swagger UI로 API 테스트해보기 (http://localhost:8000/docs)

#### 추천 학습 자료
- [ ] [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [ ] [REST API 설계 가이드](https://www.youtube.com/results?search_query=rest+api+design)

---

### 2.5 React/Vue.js - 프론트엔드 개발

#### 학습 목표
- [ ] 프론트엔드 프레임워크의 필요성 이해
- [ ] 컴포넌트 기반 개발 이해
- [ ] 상태 관리 개념 이해
- [ ] API 호출 방법 이해

#### 왜 이것을 알아야 하는가?
- Milestone 5에서 프론트엔드 프레임워크 선택을 위해
- UI/UX 설계 결정을 내리기 위해
- 프론트엔드 개발자와 협업하기 위해

#### 핵심 개념

**React vs Vue.js**
```
React:
✓ 더 큰 생태계
✓ 많은 채용 공고
✓ Facebook 개발
✗ 학습 곡선 높음

Vue.js:
✓ 쉬운 학습
✓ 한글 문서 풍부
✓ 가벼움
✗ 생태계 작음
```

**컴포넌트 기반 개발**
```
App
├── Header
├── CameraView
│   ├── VideoStream
│   └── FaceBoxes
├── FaceList
│   └── FaceCard (반복)
└── Footer
```

**프로젝트 페이지 구성 (Milestone 5)**
```
1. 메인 대시보드
   - 실시간 카메라 뷰
   - 인식된 얼굴 표시

2. 얼굴 등록 페이지
   - 카메라로 얼굴 촬영
   - 이름 입력
   - 등록 버튼

3. 얼굴 관리 페이지
   - 등록된 얼굴 목록
   - 수정/삭제 기능

4. 통계 페이지 (선택)
   - 인식 로그
   - 시간대별 통계
```

#### 관리자가 알아야 할 질문들

```
Q: React와 Vue.js 중 어떤 것을 선택할 것인가?
A:
   결정 기준:
   1. 팀의 경험
   2. 프로젝트 복잡도
   3. 학습 시간
   → [Milestone 5 시작 전 결정]

Q: 실시간 비디오 스트림을 브라우저에 어떻게 표시하는가?
A:
   1. <img> 태그로 MJPEG 스트림 표시
   2. <video> 태그로 WebRTC
   3. Canvas로 프레임별 렌더링

Q: API 호출은 어떻게 하는가?
A:
   - fetch API
   - axios 라이브러리 (추천)
```

#### 실습 과제 (Milestone 5 전)
- [ ] React 또는 Vue.js 기초 튜토리얼 완료
- [ ] 간단한 TODO 앱 만들어보기
- [ ] API 호출하는 컴포넌트 작성해보기

#### 추천 학습 자료
- [ ] [React 공식 튜토리얼](https://react.dev/learn)
- [ ] [Vue.js 공식 가이드](https://vuejs.org/guide/)
- [ ] [웹 카메라 스트리밍 예제](https://www.youtube.com/results?search_query=webcam+streaming+react)

---

## Level 3: 시스템 통합

> 이 레벨은 **개별 기술을 하나의 시스템으로 통합**하는 방법을 학습합니다.

### 3.1 전체 시스템 아키텍처 이해

#### 학습 목표
- [ ] 전체 시스템의 데이터 흐름 이해
- [ ] 각 컴포넌트 간 인터페이스 이해
- [ ] 병목 지점 파악 능력

#### 시스템 아키텍처 다이어그램

```
┌──────────────────────────────────────────────────────────────┐
│                        웹 브라우저                            │
│                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ 카메라 뷰   │  │ 얼굴 등록   │  │ 얼굴 관리   │         │
│  │ (React/Vue) │  │ (React/Vue) │  │ (React/Vue) │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         │                │                │                  │
└─────────┼────────────────┼────────────────┼──────────────────┘
          │                │                │
          │    HTTP/WebSocket/SSE           │
          │                │                │
┌─────────▼────────────────▼────────────────▼──────────────────┐
│                    FastAPI 서버                               │
│                                                               │
│  ┌────────────────────────────────────────────────┐          │
│  │              API 라우터                         │          │
│  │  /api/camera/stream                            │          │
│  │  /api/face/register                            │          │
│  │  /api/face/recognize                           │          │
│  │  /api/faces/list                               │          │
│  └───────┬────────────────────────┬────────────────┘          │
│          │                        │                           │
│  ┌───────▼──────┐         ┌───────▼────────┐                │
│  │ 카메라 모듈   │         │  얼굴 인식 모듈 │                │
│  │ (OpenCV)     │         │ (Transformers) │                │
│  └───────┬──────┘         └───────┬────────┘                │
│          │                        │                           │
└──────────┼────────────────────────┼───────────────────────────┘
           │                        │
    ┌──────▼───────┐        ┌───────▼────────┐
    │   웹캠       │        │ 얼굴 DB        │
    │ (하드웨어)   │        │ (임베딩 저장)  │
    └──────────────┘        └────────────────┘
```

#### 데이터 흐름 분석

**시나리오 1: 실시간 얼굴 인식**
```
1. 사용자: "얼굴 인식 시작" 버튼 클릭
   ↓
2. 브라우저: GET /api/camera/stream 요청
   ↓
3. 서버: 카메라에서 프레임 읽기 (OpenCV)
   ↓
4. 서버: 얼굴 감지 (Haar Cascade)
   ↓
5. 서버: 얼굴 임베딩 추출 (Transformers)
   ↓
6. 서버: DB의 임베딩과 비교
   ↓
7. 서버: 결과를 이미지에 표시 (바운딩 박스 + 이름)
   ↓
8. 서버: 브라우저로 전송
   ↓
9. 브라우저: 화면에 렌더링
   ↓
   (2번으로 반복 - 실시간 스트림)
```

**시나리오 2: 새로운 얼굴 등록**
```
1. 사용자: 이름 입력 + "얼굴 촬영" 버튼 클릭
   ↓
2. 브라우저: 카메라로 사진 촬영
   ↓
3. 브라우저: POST /api/face/register (이름 + 이미지)
   ↓
4. 서버: 얼굴 감지 (얼굴이 있는지 확인)
   ↓
5. 서버: 얼굴 임베딩 추출
   ↓
6. 서버: DB에 저장 (이름 + 임베딩 + 이미지)
   ↓
7. 서버: 성공 응답
   ↓
8. 브라우저: "등록 완료" 메시지 표시
```

#### 병목 지점 분석

```
잠재적 병목 지점:
1. 카메라 캡처 속도 (해상도에 따라)
2. AI 모델 추론 시간 (GPU 없으면 느림)
3. 네트워크 대역폭 (비디오 스트림)
4. DB 쿼리 속도 (임베딩 비교)

최적화 방향:
- 해상도 조정
- 모델 경량화
- 프레임 스킵 (30fps → 15fps)
- 비동기 처리
```

---

### 3.2 데이터베이스 설계

#### 학습 목표
- [ ] 얼굴 데이터 저장 방식 이해
- [ ] 임베딩 벡터 저장 및 비교 방법 이해
- [ ] 데이터베이스 선택 기준 이해

#### 왜 이것을 알아야 하는가?
- 얼굴 등록/삭제 기능 구현을 위해
- 성능 최적화를 위해
- 데이터 백업/복구 계획을 세우기 위해

#### 데이터베이스 스키마 설계

**옵션 1: SQLite (간단한 프로젝트)**
```sql
CREATE TABLE faces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    embedding BLOB,  -- 512차원 벡터 (직렬화)
    image_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**옵션 2: JSON 파일 (더 간단)**
```json
{
  "faces": [
    {
      "id": 1,
      "name": "홍길동",
      "embedding": [0.1, 0.2, ..., 0.5],  // 512개
      "image_path": "faces/1.jpg",
      "created_at": "2026-02-06T12:00:00"
    }
  ]
}
```

**벡터 유사도 검색**
```python
import numpy as np

def find_matching_face(query_embedding, database_embeddings, threshold=0.6):
    """
    query_embedding: 인식하려는 얼굴의 임베딩
    database_embeddings: DB에 저장된 모든 임베딩들
    threshold: 동일인 판단 임계값
    """
    similarities = []

    for db_embedding in database_embeddings:
        # 코사인 유사도 계산
        similarity = cosine_similarity(query_embedding, db_embedding)
        similarities.append(similarity)

    max_similarity = max(similarities)

    if max_similarity > threshold:
        return database_embeddings[similarities.index(max_similarity)]
    else:
        return None  # 매칭되는 얼굴 없음
```

#### 관리자가 알아야 할 질문들

```
Q: 얼굴 이미지를 DB에 저장해야 하는가?
A:
   - 임베딩만 저장: 빠름, 용량 적음, 이미지 확인 불가
   - 이미지도 저장: 느림, 용량 많음, 이미지 확인 가능
   → 둘 다 저장 추천 (임베딩 + 이미지 경로)

Q: 임베딩 벡터를 어떻게 저장하는가?
A:
   - NumPy array를 bytes로 직렬화
   - pickle, JSON, 또는 전용 벡터 DB

Q: 등록된 얼굴이 1000명이면 인식 속도는?
A:
   - 1000개 임베딩과 비교: O(n)
   - 최적화: 벡터 DB (Faiss, Pinecone)
   → 초기에는 간단한 방식, 나중에 최적화
```

---

### 3.3 에러 처리 및 로깅

#### 학습 목표
- [ ] 예외 처리의 중요성 이해
- [ ] 로깅 레벨 이해
- [ ] 디버깅 방법 습득

#### 핵심 개념

**발생 가능한 에러들**
```python
# 1. 카메라 에러
try:
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise Exception("카메라를 열 수 없습니다")
except Exception as e:
    logger.error(f"카메라 에러: {e}")
    # 사용자에게 알림

# 2. 모델 로드 에러
try:
    model = load_model("model_name")
except Exception as e:
    logger.error(f"모델 로드 실패: {e}")
    # 대체 모델 사용 또는 종료

# 3. API 에러
@app.post("/api/face/register")
async def register_face(name: str, image: UploadFile):
    try:
        # 얼굴 등록 로직
        ...
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"얼굴 등록 실패: {e}")
        raise HTTPException(status_code=500, detail="서버 에러")
```

**로깅 설정**
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# 사용
logger.debug("디버그 정보")
logger.info("일반 정보")
logger.warning("경고")
logger.error("에러")
logger.critical("심각한 에러")
```

---

## Level 4: 프로젝트 관리

> 이 레벨은 **프로젝트 관리자로서 알아야 할 실무 지식**입니다.

### 4.1 Git & GitHub 워크플로우

#### 학습 목표
- [ ] Git의 기본 개념 이해
- [ ] 브랜치 전략 이해
- [ ] GitHub Issues와 Milestone 활용법 이해

#### 핵심 개념

**Git 기본 명령어**
```bash
# 상태 확인
git status

# 변경사항 추가
git add backend/app.py

# 커밋
git commit -m "Add face recognition endpoint"

# 푸시
git push origin feature/face-recognition

# 로그 확인
git log --oneline

# 브랜치 생성
git checkout -b feature/new-feature
```

**브랜치 전략**
```
master (main)
  ├── develop
  │   ├── feature/camera-integration
  │   ├── feature/ml-model
  │   └── feature/web-dashboard
```

**GitHub Issues 활용**
```
Issue #1: [Milestone 2] 카메라 연동 구현
- [ ] OpenCV 카메라 핸들러 작성
- [ ] 실시간 스트림 테스트
- [ ] 단위 테스트 작성

레이블: enhancement, milestone-2
마일스톤: Milestone 2
담당자: @username
```

#### 관리자가 알아야 할 질문들

```
Q: 언제 커밋해야 하는가?
A:
   - 기능 하나가 완성되었을 때
   - 테스트가 통과했을 때
   - 의미 있는 단위로 묶어서

Q: 커밋 메시지는 어떻게 작성하는가?
A:
   - 명령형으로 작성 ("Add", "Fix", "Update")
   - 무엇을 했는지 간결하게
   예: "Add face detection module"

Q: 브랜치를 언제 머지하는가?
A:
   - 기능이 완전히 완성되었을 때
   - 테스트를 통과했을 때
   - 코드 리뷰를 받았을 때
```

---

### 4.2 테스트 전략

#### 학습 목표
- [ ] 테스트의 중요성 이해
- [ ] 단위 테스트 작성 방법 이해
- [ ] 통합 테스트 개념 이해

#### 테스트 레벨

```
1. 단위 테스트 (Unit Test)
   - 각 함수/클래스를 독립적으로 테스트
   - pytest 사용

2. 통합 테스트 (Integration Test)
   - 여러 모듈이 함께 작동하는지 테스트
   - 카메라 + 얼굴 감지

3. E2E 테스트 (End-to-End Test)
   - 전체 시스템 흐름 테스트
   - 브라우저 → API → DB → 응답
```

**단위 테스트 예시**
```python
# tests/test_camera_handler.py
import pytest
from backend.camera.camera_handler import CameraHandler

def test_camera_initialization():
    """카메라 초기화 테스트"""
    camera = CameraHandler(camera_id=0)
    assert camera is not None
    assert camera.is_opened()

def test_frame_capture():
    """프레임 캡처 테스트"""
    camera = CameraHandler(camera_id=0)
    frame = camera.read_frame()

    assert frame is not None
    assert frame.shape[2] == 3  # RGB 채널
```

**테스트 실행**
```bash
# 모든 테스트 실행
pytest tests/

# 특정 파일 테스트
pytest tests/test_camera_handler.py

# 커버리지 확인
pytest --cov=backend tests/
```

---

### 4.3 성능 최적화

#### 학습 목표
- [ ] 성능 병목 지점 파악 방법
- [ ] 최적화 기법 이해
- [ ] 모니터링 방법 이해

#### 성능 지표

```
목표 성능:
- 실시간 처리: > 15 FPS
- 얼굴 감지 성공률: > 95%
- 얼굴 인식 정확도: > 90%
- API 응답 시간: < 500ms
```

**성능 측정**
```python
import time

def measure_fps():
    """FPS 측정"""
    frame_count = 0
    start_time = time.time()

    while True:
        # 프레임 처리
        ...
        frame_count += 1

        elapsed_time = time.time() - start_time
        if elapsed_time > 1.0:
            fps = frame_count / elapsed_time
            print(f"FPS: {fps:.2f}")
            frame_count = 0
            start_time = time.time()

def measure_inference_time(model, image):
    """모델 추론 시간 측정"""
    start = time.time()
    result = model(image)
    end = time.time()
    print(f"추론 시간: {(end - start) * 1000:.2f}ms")
    return result
```

**최적화 기법**
```python
# 1. 해상도 축소
frame = cv2.resize(frame, (640, 480))  # 원본보다 작게

# 2. 프레임 스킵
frame_count = 0
if frame_count % 2 == 0:  # 2프레임마다 1번 처리
    detect_faces(frame)
frame_count += 1

# 3. 비동기 처리
import asyncio

async def process_frame(frame):
    result = await model.predict(frame)
    return result

# 4. GPU 사용
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)
```

---

### 4.4 보안 고려사항

#### 학습 목표
- [ ] 얼굴 데이터 보호의 중요성 이해
- [ ] 기본적인 보안 조치 이해
- [ ] GDPR/개인정보보호법 개념 이해

#### 보안 체크리스트

```
[ ] 얼굴 이미지 암호화 저장
[ ] API 인증 구현 (JWT 토큰)
[ ] HTTPS 사용
[ ] CORS 적절히 설정
[ ] 입력 검증 (SQL Injection 방지)
[ ] 개인정보 처리 방침 작성
[ ] 데이터 백업 및 복구 계획
[ ] 로그에 민감정보 기록 안 함
```

**기본 보안 조치**
```python
# 1. 입력 검증
from fastapi import HTTPException

@app.post("/api/face/register")
async def register_face(name: str, image: UploadFile):
    # 이름 길이 제한
    if len(name) > 50:
        raise HTTPException(400, "이름이 너무 깁니다")

    # 파일 타입 검증
    if not image.content_type.startswith("image/"):
        raise HTTPException(400, "이미지 파일만 업로드 가능합니다")

# 2. API 인증
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

@app.get("/api/faces/list")
async def get_faces(credentials = Depends(security)):
    # 토큰 검증
    if not verify_token(credentials.credentials):
        raise HTTPException(401, "인증 실패")
    ...
```

---

## 실전 체크리스트

### Milestone별 학습 체크리스트

#### Milestone 1: 프로젝트 초기 설정
- [ ] Python 가상환경 개념 이해
- [ ] requirements.txt 작성법 이해
- [ ] Git 기본 명령어 숙지
- [ ] 프로젝트 구조 이해

#### Milestone 2: 카메라 연동 및 얼굴 감지
- [ ] OpenCV 기초 이해
- [ ] 이미지 데이터 구조 이해
- [ ] Haar Cascade 원리 이해
- [ ] 카메라 핸들러 코드 리뷰

#### Milestone 3: ML 모델 통합
- [ ] Hugging Face 플랫폼 탐색
- [ ] 얼굴 인식 모델 비교 분석
- [ ] 얼굴 임베딩 개념 이해
- [ ] 모델 추론 과정 이해
- [ ] 성능 vs 정확도 트레이드오프 이해

#### Milestone 4: Backend API 개발
- [ ] REST API 설계 원칙 이해
- [ ] FastAPI 기초 학습
- [ ] API 엔드포인트 설계
- [ ] CORS 개념 이해
- [ ] Swagger UI 사용법

#### Milestone 5: 웹 대시보드 개발
- [ ] React 또는 Vue.js 기초 학습
- [ ] 컴포넌트 설계
- [ ] API 호출 방법
- [ ] 실시간 스트리밍 구현 방법

#### Milestone 6: 통합 및 배포
- [ ] 통합 테스트 방법
- [ ] 성능 측정 및 최적화
- [ ] 보안 점검
- [ ] 배포 옵션 조사

---

## 문제 해결 가이드

### 자주 발생하는 문제와 해결 방법

#### 문제 1: 카메라가 열리지 않음
```
증상: cv2.VideoCapture(0) 실패

체크리스트:
[ ] 다른 프로그램이 카메라를 사용 중인가?
[ ] WSL 환경인가? (WSL은 카메라 접근 제한)
[ ] 카메라 권한이 있는가?
[ ] 카메라 ID가 올바른가? (0, 1, 2 시도)

해결 방법:
1. 다른 프로그램 종료
2. 권한 확인
3. 다른 ID 시도
4. 네이티브 Linux/Windows 환경 사용
```

#### 문제 2: 모델 로드 실패
```
증상: transformers 모델 로드 시 에러

체크리스트:
[ ] 인터넷 연결이 되어 있는가? (모델 다운로드)
[ ] 디스크 공간이 충분한가? (모델 크기 2-5GB)
[ ] 모델 이름이 올바른가?
[ ] torch 버전이 호환되는가?

해결 방법:
1. 인터넷 연결 확인
2. 디스크 공간 확보
3. Hugging Face에서 모델 이름 확인
4. torch 재설치
```

#### 문제 3: FPS가 너무 낮음
```
증상: 실시간 처리가 버벅임 (< 10 FPS)

원인 분석:
1. 카메라 해상도가 너무 높음
2. AI 모델이 너무 무거움
3. GPU를 사용하지 않음
4. 네트워크 전송이 느림

해결 방법:
1. 해상도 축소: (1920x1080) → (640x480)
2. 경량 모델 사용
3. GPU 활성화 (CUDA)
4. 프레임 스킵 적용
5. 압축률 조정
```

#### 문제 4: CORS 에러
```
증상: 브라우저에서 API 호출 시 CORS 에러

해결 방법:
1. FastAPI에 CORSMiddleware 추가
2. allow_origins에 프론트엔드 URL 추가
3. allow_methods, allow_headers 설정
```

#### 문제 5: 얼굴 인식 정확도가 낮음
```
원인 분석:
1. 조명이 좋지 않음
2. 얼굴 각도 문제
3. 저화질 이미지
4. 임계값 설정 문제

해결 방법:
1. 조명 개선
2. 정면 얼굴 촬영 유도
3. 카메라 해상도 향상
4. 임계값 조정 (0.5 → 0.7)
5. 더 정확한 모델 사용
```

---

## 추가 학습 자료

### 온라인 강의 추천
- [ ] [CS50's Introduction to AI](https://cs50.harvard.edu/ai/)
- [ ] [Fast.ai - Practical Deep Learning](https://www.fast.ai/)
- [ ] [OpenCV Python Tutorial](https://www.youtube.com/watch?v=oXlwWbU8l2o)

### 읽을만한 글
- [ ] [Face Recognition: From Traditional to Deep Learning Methods](https://arxiv.org/abs/1811.00116)
- [ ] [REST API Design Best Practices](https://stackoverflow.blog/2020/03/02/best-practices-for-rest-api-design/)

### 실습 프로젝트
- [ ] [얼굴 감지 기초 프로젝트](https://www.pyimagesearch.com/2018/02/26/face-detection-with-opencv-and-deep-learning/)
- [ ] [FastAPI 튜토리얼](https://fastapi.tiangolo.com/tutorial/)

---

## 학습 로그

### 주차별 학습 기록

#### Week 1 (Milestone 1)
```
학습 내용:
- [ ] Python 가상환경
- [ ] Git 기본 명령어
- [ ] 프로젝트 구조 이해

이해한 것:
-

질문/막힌 부분:
-

다음 주 계획:
-
```

#### Week 2 (Milestone 2)
```
학습 내용:
- [ ] OpenCV 기초
- [ ] 이미지 처리
- [ ] 얼굴 감지

이해한 것:
-

질문/막힌 부분:
-

다음 주 계획:
-
```

#### Week 3-4 (Milestone 3)
```
학습 내용:
- [ ] Hugging Face 모델 조사
- [ ] 얼굴 임베딩
- [ ] 모델 통합

선택한 모델:
-

이유:
-

성능 테스트 결과:
-

질문/막힌 부분:
-

다음 주 계획:
-
```

---

## 용어 사전

### A-E
- **API (Application Programming Interface)**: 프로그램 간 통신 인터페이스
- **Batch Size**: 한 번에 처리하는 데이터 개수
- **BGR**: Blue-Green-Red 색상 순서 (OpenCV 기본)
- **Cascade**: 연속적인 분류기 체인
- **CORS (Cross-Origin Resource Sharing)**: 도메인 간 리소스 공유
- **Embedding**: 고차원 데이터를 저차원 벡터로 표현

### F-J
- **FastAPI**: Python 기반 웹 프레임워크
- **FPS (Frames Per Second)**: 초당 프레임 수
- **GPU (Graphics Processing Unit)**: 그래픽 처리 장치, AI 연산에 사용
- **Haar Cascade**: 얼굴 감지 알고리즘
- **HTTP (Hypertext Transfer Protocol)**: 웹 통신 프로토콜
- **Inference**: 학습된 모델로 예측하는 과정

### K-O
- **MJPEG**: Motion JPEG, 비디오 스트리밍 포맷
- **NumPy**: Python 수치 연산 라이브러리
- **OpenCV**: 컴퓨터 비전 라이브러리

### P-T
- **Pixel**: 이미지의 최소 단위
- **PyTorch**: 딥러닝 프레임워크
- **REST (Representational State Transfer)**: API 설계 아키텍처
- **RGB**: Red-Green-Blue 색상 순서
- **Transformers**: Hugging Face의 ML 라이브러리

### U-Z
- **Uvicorn**: FastAPI를 실행하는 ASGI 서버
- **Vector**: 숫자의 배열, 임베딩 표현
- **WebSocket**: 양방향 실시간 통신 프로토콜

---

## 마치며

### 학습 원칙 다시 한번

1. **제1원칙으로 돌아가기**
   - 복잡하면 가장 단순한 요소로 분해
   - "왜?"를 계속 질문하기

2. **실제 코드와 연결하기**
   - 이론만 공부하지 말고 코드 확인
   - 직접 실행해보고 수정해보기

3. **문제 해결 중심**
   - 에러가 나면 좋은 학습 기회
   - 에러 메시지를 읽고 이해하기

4. **점진적 학습**
   - 한 번에 모든 것을 이해하려 하지 말기
   - Milestone별로 필요한 것만 학습

### 프로젝트 관리자로서 명심할 것

```
"모든 코드를 작성할 필요는 없지만,
 모든 기술의 WHY는 이해해야 한다"
```

- AI가 코드를 작성하더라도, 의사결정은 사람이 한다
- 기술 선택의 이유를 알아야 한다
- 트레이드오프를 이해해야 한다
- 문제가 생겼을 때 원인을 추적할 수 있어야 한다

---

**최종 업데이트**: 2026-02-06
**다음 업데이트 예정**: Milestone 3 완료 후
