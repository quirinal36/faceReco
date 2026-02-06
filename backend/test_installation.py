"""
Installation Verification Script

Tests if all required packages are correctly installed
and can be imported without errors.
"""

import sys


def check_package(package_name, import_name=None):
    """
    Check if a package is installed and can be imported

    Args:
        package_name (str): Display name of the package
        import_name (str): Import name (if different from package_name)

    Returns:
        bool: True if package is installed, False otherwise
    """
    if import_name is None:
        import_name = package_name

    try:
        __import__(import_name)
        print(f"[OK] {package_name} is installed")
        return True
    except ImportError as e:
        print(f"[FAIL] {package_name} is NOT installed: {str(e)}")
        return False


def check_insightface():
    """
    Check InsightFace installation in detail

    Returns:
        bool: True if InsightFace is working, False otherwise
    """
    print("\n" + "=" * 60)
    print("InsightFace Detailed Check")
    print("=" * 60)

    try:
        import insightface
        print(f"[OK] InsightFace version: {insightface.__version__}")

        # Try importing FaceAnalysis
        try:
            from insightface.app import FaceAnalysis
            print("[OK] FaceAnalysis can be imported")

            # Try initializing the model (this may download files)
            print("\nAttempting to initialize FaceAnalysis model...")
            print("(This may take a while on first run - downloading ~600MB)")

            try:
                app = FaceAnalysis(name='buffalo_l')
                app.prepare(ctx_id=-1)  # Use CPU
                print("[OK] InsightFace model initialized successfully!")
                print("[OK] Face recognition is ready to use")
                return True
            except Exception as e:
                print(f"[WARN] Model initialization failed: {str(e)}")
                print("[INFO] This may be due to:")
                print("  - First-time model download in progress")
                print("  - Network connection issues")
                print("  - Incompatible InsightFace version")
                print("[INFO] Try running the face recognition demo:")
                print("  python app.py --mode face_recognition")
                return False

        except ImportError as e:
            print(f"[FAIL] Cannot import FaceAnalysis: {str(e)}")
            print("[INFO] You may have an old version of InsightFace")
            print("[INFO] See TROUBLESHOOTING.md for solutions")
            return False

    except ImportError as e:
        print(f"[FAIL] InsightFace is not installed: {str(e)}")
        print("[INFO] Install with: pip install insightface")
        print("[INFO] On Windows, see TROUBLESHOOTING.md")
        return False


def check_onnxruntime():
    """
    Check ONNX Runtime and available providers

    Returns:
        bool: True if ONNX Runtime is working, False otherwise
    """
    try:
        import onnxruntime as ort
        print(f"[OK] ONNX Runtime version: {ort.__version__}")

        providers = ort.get_available_providers()
        print(f"[INFO] Available execution providers: {', '.join(providers)}")

        if 'CUDAExecutionProvider' in providers:
            print("[OK] GPU (CUDA) acceleration is available")
        else:
            print("[INFO] Running on CPU (GPU not available)")

        return True
    except Exception as e:
        print(f"[FAIL] ONNX Runtime error: {str(e)}")
        return False


def main():
    """Main function to run all checks"""
    print("=" * 60)
    print("Face Recognition System - Installation Check")
    print("=" * 60)
    print()

    # Core packages
    packages = [
        ('FastAPI', 'fastapi'),
        ('Uvicorn', 'uvicorn'),
        ('OpenCV', 'cv2'),
        ('NumPy', 'numpy'),
        ('Scikit-learn', 'sklearn'),
        ('Pillow', 'PIL'),
        ('Pydantic', 'pydantic'),
    ]

    print("Checking core packages...")
    print("-" * 60)
    all_ok = True
    for pkg, imp in packages:
        if not check_package(pkg, imp):
            all_ok = False

    # Check ONNX Runtime
    print()
    print("Checking ONNX Runtime...")
    print("-" * 60)
    if not check_onnxruntime():
        all_ok = False

    # Check InsightFace (detailed)
    if not check_insightface():
        all_ok = False

    # Summary
    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)

    if all_ok:
        print("[SUCCESS] All packages are correctly installed!")
        print()
        print("You can now:")
        print("  1. Run the API server:")
        print("     python server.py")
        print()
        print("  2. Test face recognition:")
        print("     python app.py --mode face_recognition")
        print()
        print("  3. Register new faces:")
        print("     python app.py --mode register")
        print()
        print("For more information, see:")
        print("  - API_GUIDE.md")
        print("  - README.md")
    else:
        print("[ERROR] Some packages are missing or have errors.")
        print()
        print("Please check the errors above and:")
        print("  1. Install missing packages:")
        print("     pip install -r requirements.txt")
        print()
        print("  2. If InsightFace installation fails on Windows:")
        print("     See TROUBLESHOOTING.md for detailed solutions")
        print()
        print("  3. For other issues:")
        print("     Check the error messages above")

    print("=" * 60)

    # Return exit code
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
