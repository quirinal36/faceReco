"""
얼굴 인식 프로그램 메인 애플리케이션

이 파일은 백엔드 서버의 진입점입니다.
"""

import sys
import argparse
from camera.camera_handler import CameraHandler, test_camera
from models.face_detection import FaceDetector, demo_face_detection
from models.face_recognition import demo_face_registration, demo_face_recognition


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='얼굴 인식 프로그램')
    parser.add_argument(
        '--mode',
        type=str,
        choices=['camera', 'face_detection', 'face_recognition', 'register', 'server'],
        default='face_detection',
        help='실행 모드 (camera: 카메라 테스트, face_detection: 얼굴 감지 데모, '
             'face_recognition: 얼굴 인식, register: 얼굴 등록, server: API 서버)'
    )
    parser.add_argument(
        '--camera-id',
        type=int,
        default=0,
        help='카메라 ID (기본값: 0)'
    )

    args = parser.parse_args()

    print("=" * 50)
    print("얼굴 인식 프로그램")
    print("=" * 50)

    try:
        if args.mode == 'camera':
            print("\n[카메라 테스트 모드]")
            test_camera(camera_id=args.camera_id)

        elif args.mode == 'face_detection':
            print("\n[얼굴 감지 데모 모드]")
            demo_face_detection(camera_id=args.camera_id)

        elif args.mode == 'register':
            print("\n[얼굴 등록 모드]")
            demo_face_registration(camera_id=args.camera_id)

        elif args.mode == 'face_recognition':
            print("\n[얼굴 인식 모드]")
            demo_face_recognition(camera_id=args.camera_id)

        elif args.mode == 'server':
            print("\n[API 서버 모드]")
            print("FastAPI 서버를 시작합니다...")
            print("=" * 50)

            # server.py의 main 함수 호출
            try:
                from server import main as server_main
                server_main()
            except ImportError as e:
                print(f"서버 모듈 로드 실패: {str(e)}")
                print("필요한 패키지를 설치하세요: pip install fastapi uvicorn")
                sys.exit(1)

    except KeyboardInterrupt:
        print("\n프로그램을 종료합니다.")
    except Exception as e:
        print(f"\n오류 발생: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
