# Troubleshooting Guide

## InsightFace Installation Issues

### Problem Description

When running `pip install insightface` on Windows, you may encounter the following build error:

```
Building wheel for insightface (pyproject.toml): finished with status 'error'
error: Microsoft Visual C++ 14.0 or greater is required
```

Or

```bash
pip install insightface --prefer-binary
```

When running the above command, InsightFace 0.2.1 (older version) will be installed, but the following error occurs:

```python
AssertionError: 'detection' not in self.models
```

---

## Root Cause Analysis

### 1. **Build Failure Cause**
The latest version of InsightFace (0.7.3+) includes C++ extension modules that need to be built from source code. On Windows, the following are required:
- **Microsoft Visual C++ Build Tools**
- **Cython**
- **C++ Compiler**

### 2. **Older Version Installation Issues**
Using the `--prefer-binary` option installs a pre-built wheel (0.2.1), but this version has:
- Missing or incomplete `FaceAnalysis` API
- No support for buffalo_l, buffalo_m, buffalo_s models
- Lack of compatibility with latest ONNX models

---

## Solutions

### ✅ Solution 1: Install Visual Studio Build Tools (Recommended)

This is the most reliable method. Once installed, you can install other C++ packages without issues in the future.

#### Steps:

1. **Download Build Tools**
   - Download [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
   - Or download Visual Studio Community Edition

2. **Select Workload**
   - During installation, select "Desktop development with C++" workload
   - Required components:
     - MSVC v142 - VS 2019 C++ x64/x86 build tools
     - Windows 10 SDK
     - C++ CMake tools for Windows

3. **After Installation**
   ```bash
   # System restart (recommended)

   # Install InsightFace
   pip install insightface onnxruntime
   ```

4. **Verify Installation**
   ```bash
   python -c "from insightface.app import FaceAnalysis; print('Success!')"
   ```

**Time Required**: About 30 minutes (download + installation)
**Disk Space**: About 6-8 GB

---

### ✅ Solution 2: Use Conda Environment (Fast and Easy)

Conda provides pre-compiled packages, so you can install without compilation.

#### Steps:

1. **Install Miniconda or Anaconda**
   - [Download Miniconda](https://docs.conda.io/en/latest/miniconda.html)

2. **Create and Activate Virtual Environment**
   ```bash
   conda create -n faceReco python=3.10
   conda activate faceReco
   ```

3. **Install Packages**
   ```bash
   # Install from conda-forge channel
   conda install -c conda-forge insightface onnxruntime

   # Install additional packages
   pip install fastapi uvicorn python-multipart opencv-python scikit-learn
   ```

4. **Run Project**
   ```bash
   cd backend
   python server.py
   ```

**Advantages**:
- No build tools required
- Fast installation (5-10 minutes)
- Environment isolation

**Disadvantages**:
- Requires Conda installation (about 500MB)

---

### ✅ Solution 3: Use Pre-built Wheel

You can use pre-built wheels provided by some communities.

#### Steps:

1. **Christoph Gohlke's Wheel Repository**
   - [https://www.lfd.uci.edu/~gohlke/pythonlibs/](https://www.lfd.uci.edu/~gohlke/pythonlibs/)
   - Search for insightface
   - Download .whl file matching your Python version and platform

2. **Install Downloaded Wheel**
   ```bash
   pip install path/to/insightface‑0.7.3‑cp310‑cp310‑win_amd64.whl
   pip install onnxruntime
   ```

**Note**: Latest versions may not always be available.

---

### ✅ Solution 4: Use WSL2 (Linux Environment)

Using Windows Subsystem for Linux allows you to install as if on Linux.

#### Steps:

1. **Install WSL2**
   ```powershell
   # PowerShell (Administrator privileges)
   wsl --install
   ```

2. **Run Ubuntu and Install Packages**
   ```bash
   # Ubuntu terminal
   sudo apt update
   sudo apt install python3-pip python3-dev

   # Install InsightFace
   pip3 install insightface onnxruntime
   pip3 install fastapi uvicorn opencv-python scikit-learn
   ```

3. **Run Project**
   ```bash
   cd /mnt/c/Users/YourName/Documents/GitHub/faceReco/backend
   python3 server.py
   ```

**Advantages**:
- All benefits of Linux environment
- Easy GPU support (WSL2 + CUDA)

**Disadvantages**:
- Requires WSL2 installation
- Possible performance degradation when accessing Windows file system

---

### ✅ Solution 5: Use Docker

Using Docker allows you to run the project independently of the environment.

#### Dockerfile Example:

```dockerfile
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Working directory
WORKDIR /app

# Install packages
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY backend/ .

# Expose port
EXPOSE 8000

# Run server
CMD ["python", "server.py"]
```

#### Execution:

```bash
# Build Docker image
docker build -t face-recognition-api .

# Run container
docker run -p 8000:8000 face-recognition-api
```

---

## Additional Troubleshooting

### Issue: `onnxruntime` Related Error

**Symptom**:
```
ImportError: cannot import name 'get_available_providers' from 'onnxruntime'
```

**Solution**:
```bash
pip uninstall onnxruntime onnxruntime-gpu
pip install onnxruntime==1.16.0
```

---

### Issue: Model Download Failure

**Symptom**:
```
RuntimeError: Failed to download model: buffalo_l
```

**Cause**: Internet connection issues or firewall

**Solution**:
1. Check network connection
2. Configure proxy (if needed)
   ```bash
   export HTTP_PROXY=http://proxy:port
   export HTTPS_PROXY=http://proxy:port
   ```
3. Manual download:
   - [InsightFace Model Zoo](https://github.com/deepinsight/insightface/tree/master/model_zoo)
   - Save to `~/.insightface/models/` directory

---

### Issue: CUDA Error When Using GPU

**Symptom**:
```
CUDAExecutionProvider is not available
```

**Solution**:
```bash
# Remove CPU version
pip uninstall onnxruntime

# Install GPU version
pip install onnxruntime-gpu==1.16.0

# Verify CUDA
python -c "import onnxruntime; print(onnxruntime.get_available_providers())"
```

**Requirements**:
- NVIDIA GPU
- CUDA Toolkit 11.x or 12.x
- cuDNN 8.x

---

## Recommended Installation Order (Windows)

### For Beginners:
1. **Install Miniconda** (Solution 2)
2. Create Conda environment and install packages
3. Run project

### For Advanced Users:
1. **Install Visual Studio Build Tools** (Solution 1)
2. Install all packages with pip
3. Configure GPU acceleration (optional)

---

## Installation Verification Script

You can verify that the installation was done correctly with the following script:

```python
# test_installation.py
import sys

def check_package(package_name, import_name=None):
    """Check package installation"""
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
    """Detailed InsightFace check"""
    try:
        from insightface.app import FaceAnalysis
        print("✓ InsightFace FaceAnalysis is available")

        # Test model initialization
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

**Execution**:
```bash
python test_installation.py
```

---

## Frequently Asked Questions (FAQ)

### Q1: Which Python version should I use?
**A**: Python 3.8 - 3.10 is recommended. Python 3.11 may not be supported by some packages yet.

### Q2: Do I have to use a virtual environment?
**A**: Highly recommended. It helps prevent dependency conflicts with other projects.

### Q3: Is GPU required?
**A**: No. Real-time face recognition is possible with CPU only. Using GPU will make it faster.

### Q4: Do the same issues occur on macOS?
**A**: On macOS, Xcode Command Line Tools are required, but installation is generally easier:
```bash
xcode-select --install
pip install insightface
```

### Q5: How do I install on Linux?
**A**: Linux is the easiest:
```bash
sudo apt-get install build-essential python3-dev
pip install insightface onnxruntime
```

---

## Additional Resources

- [InsightFace Official Documentation](https://github.com/deepinsight/insightface)
- [ONNX Runtime Official Documentation](https://onnxruntime.ai/)
- [FastAPI Official Documentation](https://fastapi.tiangolo.com/)
- [Project GitHub Issues](https://github.com/yourusername/faceReco/issues)

---

## Need Help?

If the problem persists after trying all the above methods:

1. **Create GitHub Issue**
   - Copy the entire error message
   - Specify Python version and OS version
   - Specify attempted solutions

2. **Collect Information**
   ```bash
   python --version
   pip --version
   pip list | grep -E "insightface|onnxruntime|opencv"
   ```

3. **Attach Log Files**
   - Installation logs
   - Execution error logs

---

**Created**: 2026-02-06
**Last Updated**: 2026-02-06
**Author**: Claude Code Assistant
