# 얼굴 인식 프로그램 (Face Recognition System)

실시간 얼굴 감지 및 인식 시스템

## 프로젝트 소개
카메라를 통한 실시간 얼굴 인식 및 웹 대시보드를 제공하는 시스템입니다.

## 주요 기능
- 실시간 카메라 연동
- Hugging Face 모델을 활용한 얼굴 인식
- 웹 기반 모니터링 대시보드
- 얼굴 등록 및 관리

## 기술 스택
- **Backend**: Python, Flask/FastAPI, OpenCV
- **ML**: Hugging Face Transformers, PyTorch
- **Frontend**: React/Vue.js
- **DevOps**: Git, GitHub

## 문서
- [PRD (제품 요구사항)](./PRD.md)
- [프로젝트 계획서](./PROJECT_PLAN.md)

## 프로젝트 구조
```
faceReco/
├── backend/                # 백엔드 서버
│   ├── app.py             # 메인 애플리케이션
│   ├── models/            # ML 모델 모듈
│   ├── camera/            # 카메라 처리 모듈
│   ├── api/               # API 엔드포인트
│   └── requirements.txt   # Python 의존성
├── frontend/              # 프론트엔드 (추후 개발)
├── docs/                  # 문서
├── tests/                 # 테스트 코드
├── PRD.md                 # 제품 요구사항
├── PROJECT_PLAN.md        # 프로젝트 계획서
└── README.md              # 이 파일
```

## 프로젝트 상태
현재 상태: **Milestone 1 - 초기 설정 완료** ✅

### 완료된 작업
- [x] GitHub 리포지토리 생성
- [x] 프로젝트 디렉토리 구조 생성
- [x] Python 가상환경 설정
- [x] 기본 의존성 패키지 설치
- [x] 문서 작성 (PRD, PROJECT_PLAN, README)

### 다음 단계
- [ ] 카메라 연동 구현 (Milestone 2)
- [ ] 얼굴 감지 기능 구현 (Milestone 2)

## 시작하기

### 사전 요구사항
- Python 3.8 이상
- Git
- 웹캠 (카메라 기능 사용 시)

### 설치 방법

1. **리포지토리 클론**
   ```bash
   git clone https://github.com/quirinal36/faceReco.git
   cd faceReco
   ```

2. **Python 가상환경 생성 및 활성화**
   ```bash
   # 가상환경 생성
   python3 -m venv venv

   # 가상환경 활성화 (Linux/Mac)
   source venv/bin/activate

   # 가상환경 활성화 (Windows)
   venv\Scripts\activate
   ```

3. **의존성 패키지 설치**
   ```bash
   # 기본 패키지 설치
   pip install -r backend/requirements.txt

   # ML 모델 패키지 (선택사항, 크기가 큼)
   # pip install torch transformers
   ```

### 실행 방법

현재 개발 초기 단계로 기본 애플리케이션만 실행 가능합니다:

```bash
# 가상환경이 활성화된 상태에서
python backend/app.py
```

### 개발 환경 설정

1. **코드 포맷팅**
   ```bash
   # Black을 이용한 코드 포맷팅
   black backend/
   ```

2. **테스트 실행**
   ```bash
   # pytest를 이용한 테스트
   pytest tests/
   ```

## 개발 가이드

### 개발 워크플로우
1. 이슈 생성 또는 선택
2. 새 브랜치 생성 (`git checkout -b feature/이슈명`)
3. 코드 작성 및 테스트
4. 커밋 및 푸시
5. Pull Request 생성

### 코딩 스타일
- Python: PEP 8 준수, Black 포맷터 사용
- 함수 및 클래스에 docstring 작성
- 테스트 코드 작성 권장

## GitHub 이슈 및 마일스톤
프로젝트 진행 상황은 [GitHub Issues](https://github.com/quirinal36/faceReco/issues)에서 확인할 수 있습니다.

### 마일스톤
- **Milestone 1**: 프로젝트 초기 설정 ✅
- **Milestone 2**: 카메라 연동 및 기본 얼굴 감지
- **Milestone 3**: ML 모델 통합
- **Milestone 4**: Backend API 개발
- **Milestone 5**: 웹 대시보드 개발
- **Milestone 6**: 통합 및 배포 준비

## 라이선스
TBD

---
최종 업데이트: 2026-02-06
