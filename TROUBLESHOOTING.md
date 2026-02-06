# 트러블슈팅 가이드

## InsightFace 설치 문제

### 문제 상황

Windows 환경에서 `pip install insightface`를 실행하면 다음과 같은 빌드 오류가 발생합니다:

```
Building wheel for insightface (pyproject.toml): finished with status 'error'
error: Microsoft Visual C++ 14.0 or greater is required
```

또는

```bash
pip install insightface --prefer-binary
```

를 실행하면 InsightFace 0.2.1 (구버전)이 설치되지만, 다음 오류가 발생합니다:

```python
AssertionError: 'detection' not in self.models
```

---

## 원인 분석

### 1. **빌드 실패 원인**
InsightFace 최신 버전(0.7.3+)은 C++ 확장 모듈을 포함하고 있어 소스 코드에서 빌드가 필요합니다. Windows에서는 다음이 필요합니다:
- **Microsoft Visual C++ Build Tools**
- **Cython**
- **C++ 컴파일러**

### 2. **구버전 설치 문제**
`--prefer-binary` 옵션을 사용하면 pre-built wheel (0.2.1)이 설치되지만, 이 버전은:
- `FaceAnalysis` API가 없거나 불완전함
- buffalo_l, buffalo_m, buffalo_s 모델 미지원
- 최신 ONNX 모델 호환성 부족

---

## 해결 방법

### ✅ 해결책 1: Visual Studio Build Tools 설치 (권장)

가장 확실한 방법입니다. 한 번 설치하면 향후 다른 C++ 패키지도 문제없이 설치할 수 있습니다.

#### 단계:

1. **Build Tools 다운로드**
   - [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) 다운로드
   - 또는 Visual Studio Community Edition 다운로드

2. **워크로드 선택**
   - 설치 시 "Desktop development with C++" 워크로드 선택
   - 필수 구성 요소:
     - MSVC v142 - VS 2019 C++ x64/x86 build tools
     - Windows 10 SDK
     - C++ CMake tools for Windows

3. **설치 완료 후**
   ```bash
   # 시스템 재시작 (권장)

   # InsightFace 설치
   pip install insightface onnxruntime
   ```

4. **설치 확인**
   ```bash
   python -c "from insightface.app import FaceAnalysis; print('Success!')"
   ```

**소요 시간**: 약 30분 (다운로드 + 설치)
**디스크 용량**: 약 6-8 GB

---

### ✅ 해결책 2: Conda 환경 사용 (빠르고 간편)

Conda는 pre-compiled 패키지를 제공하므로 컴파일 없이 설치할 수 있습니다.

#### 단계:

1. **Miniconda 또는 Anaconda 설치**
   - [Miniconda 다운로드](https://docs.conda.io/en/latest/miniconda.html)

2. **가상환경 생성 및 활성화**
   ```bash
   conda create -n faceReco python=3.10
   conda activate faceReco
   ```

3. **패키지 설치**
   ```bash
   # Conda-forge 채널에서 설치
   conda install -c conda-forge insightface onnxruntime

   # 추가 패키지 설치
   pip install fastapi uvicorn python-multipart opencv-python scikit-learn
   ```

4. **프로젝트 실행**
   ```bash
   cd backend
   python server.py
   ```

**장점**:
- 빌드 도구 불필요
- 빠른 설치 (5-10분)
- 환경 격리

**단점**:
- Conda 추가 설치 필요 (약 500MB)

---

### ✅ 해결책 3: Pre-built Wheel 사용

일부 커뮤니티에서 제공하는 pre-built wheel을 사용할 수 있습니다.

#### 단계:

1. **Christoph Gohlke's Wheel Repository**
   - [https://www.lfd.uci.edu/~gohlke/pythonlibs/](https://www.lfd.uci.edu/~gohlke/pythonlibs/)
   - insightface 검색
   - Python 버전 및 플랫폼에 맞는 .whl 파일 다운로드

2. **다운로드한 Wheel 설치**
   ```bash
   pip install path/to/insightface‑0.7.3‑cp310‑cp310‑win_amd64.whl
   pip install onnxruntime
   ```

**주의**: 최신 버전이 항상 제공되지는 않습니다.

---

### ✅ 해결책 4: WSL2 사용 (Linux 환경)

Windows Subsystem for Linux를 사용하면 Linux처럼 설치할 수 있습니다.

#### 단계:

1. **WSL2 설치**
   ```powershell
   # PowerShell (관리자 권한)
   wsl --install
   ```

2. **Ubuntu 실행 및 패키지 설치**
   ```bash
   # Ubuntu 터미널
   sudo apt update
   sudo apt install python3-pip python3-dev

   # InsightFace 설치
   pip3 install insightface onnxruntime
   pip3 install fastapi uvicorn opencv-python scikit-learn
   ```

3. **프로젝트 실행**
   ```bash
   cd /mnt/c/Users/YourName/Documents/GitHub/faceReco/backend
   python3 server.py
   ```

**장점**:
- Linux 환경의 모든 이점
- GPU 지원 용이 (WSL2 + CUDA)

**단점**:
- WSL2 설치 필요
- Windows 파일 시스템 접근 시 성능 저하 가능

---

### ✅ 해결책 5: Docker 사용

Docker를 사용하면 환경 독립적으로 실행할 수 있습니다.

#### Dockerfile 예시:

```dockerfile
FROM python:3.10-slim

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리
WORKDIR /app

# 패키지 설치
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 복사
COPY backend/ .

# 포트 노출
EXPOSE 8000

# 서버 실행
CMD ["python", "server.py"]
```

#### 실행:

```bash
# Docker 이미지 빌드
docker build -t face-recognition-api .

# 컨테이너 실행
docker run -p 8000:8000 face-recognition-api
```

---

## 추가 문제 해결

### 문제: `onnxruntime` 관련 오류

**증상**:
```
ImportError: cannot import name 'get_available_providers' from 'onnxruntime'
```

**해결**:
```bash
pip uninstall onnxruntime onnxruntime-gpu
pip install onnxruntime==1.16.0
```

---

### 문제: 모델 다운로드 실패

**증상**:
```
RuntimeError: Failed to download model: buffalo_l
```

**원인**: 인터넷 연결 문제 또는 방화벽

**해결**:
1. 네트워크 연결 확인
2. 프록시 설정 (필요시)
   ```bash
   export HTTP_PROXY=http://proxy:port
   export HTTPS_PROXY=http://proxy:port
   ```
3. 수동 다운로드:
   - [InsightFace Model Zoo](https://github.com/deepinsight/insightface/tree/master/model_zoo)
   - `~/.insightface/models/` 디렉토리에 저장

---

### 문제: GPU 사용 시 CUDA 오류

**증상**:
```
CUDAExecutionProvider is not available
```

**해결**:
```bash
# CPU 버전 제거
pip uninstall onnxruntime

# GPU 버전 설치
pip install onnxruntime-gpu==1.16.0

# CUDA 확인
python -c "import onnxruntime; print(onnxruntime.get_available_providers())"
```

**요구사항**:
- NVIDIA GPU
- CUDA Toolkit 11.x 또는 12.x
- cuDNN 8.x

---

## 권장 설치 순서 (Windows)

### 초보자용:
1. **Miniconda 설치** (해결책 2)
2. Conda 환경 생성 및 패키지 설치
3. 프로젝트 실행

### 숙련자용:
1. **Visual Studio Build Tools 설치** (해결책 1)
2. pip로 모든 패키지 설치
3. GPU 가속 설정 (선택사항)

---

## 설치 확인 스크립트

다음 스크립트로 설치가 제대로 되었는지 확인할 수 있습니다:

```python
# test_installation.py
import sys

def check_package(package_name, import_name=None):
    """패키지 설치 확인"""
    if import_name is None:
        import_name = package_name

    try:
        __import__(import_name)
        print(f"✓ {package_name} is installed")
        return True
    except ImportError:
        print(f"✗ {package_name} is NOT installed")
        return False

def check_insightface():
    """InsightFace 상세 확인"""
    try:
        from insightface.app import FaceAnalysis
        print("✓ InsightFace FaceAnalysis is available")

        # 모델 초기화 테스트
        app = FaceAnalysis(name='buffalo_l')
        print("✓ InsightFace model can be initialized")
        return True
    except Exception as e:
        print(f"✗ InsightFace error: {str(e)}")
        return False

def main():
    print("=" * 60)
    print("Package Installation Check")
    print("=" * 60)

    packages = [
        ('opencv-python', 'cv2'),
        ('numpy', 'numpy'),
        ('scikit-learn', 'sklearn'),
        ('fastapi', 'fastapi'),
        ('uvicorn', 'uvicorn'),
        ('onnxruntime', 'onnxruntime'),
    ]

    all_ok = True
    for pkg, imp in packages:
        if not check_package(pkg, imp):
            all_ok = False

    print()
    if not check_insightface():
        all_ok = False

    print("=" * 60)
    if all_ok:
        print("✓ All packages are correctly installed!")
        print("You can now run the server with: python server.py")
    else:
        print("✗ Some packages are missing or have errors.")
        print("Please refer to TROUBLESHOOTING.md for solutions.")
    print("=" * 60)

if __name__ == "__main__":
    main()
```

**실행**:
```bash
python test_installation.py
```

---

## 자주 묻는 질문 (FAQ)

### Q1: Python 버전은 어떤 것을 사용해야 하나요?
**A**: Python 3.8 - 3.10을 권장합니다. Python 3.11은 일부 패키지가 아직 지원하지 않을 수 있습니다.

### Q2: 가상환경을 꼭 사용해야 하나요?
**A**: 강력히 권장합니다. 다른 프로젝트와의 의존성 충돌을 방지할 수 있습니다.

### Q3: GPU가 필수인가요?
**A**: 아닙니다. CPU만으로도 실시간 얼굴 인식이 가능합니다. GPU를 사용하면 더 빠릅니다.

### Q4: macOS에서도 같은 문제가 발생하나요?
**A**: macOS에서는 Xcode Command Line Tools가 필요하지만, 일반적으로 더 쉽게 설치됩니다:
```bash
xcode-select --install
pip install insightface
```

### Q5: Linux에서 설치 방법은?
**A**: Linux가 가장 쉽습니다:
```bash
sudo apt-get install build-essential python3-dev
pip install insightface onnxruntime
```

---

## 추가 리소스

- [InsightFace 공식 문서](https://github.com/deepinsight/insightface)
- [ONNX Runtime 공식 문서](https://onnxruntime.ai/)
- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [프로젝트 GitHub Issues](https://github.com/yourusername/faceReco/issues)

---

## 도움이 필요하신가요?

위의 모든 방법을 시도해도 문제가 해결되지 않으면:

1. **GitHub Issue 생성**
   - 에러 메시지 전체 복사
   - Python 버전, OS 버전 명시
   - 시도한 해결 방법 명시

2. **정보 수집**
   ```bash
   python --version
   pip --version
   pip list | grep -E "insightface|onnxruntime|opencv"
   ```

3. **로그 파일 첨부**
   - 설치 로그
   - 실행 오류 로그

---

**작성일**: 2026-02-06
**최종 업데이트**: 2026-02-06
**작성자**: Claude Code Assistant
