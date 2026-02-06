"""
얼굴 인식 프로그램 메인 애플리케이션

이 파일은 백엔드 서버의 진입점입니다.
"""

import sys
import argparse
from camera.camera_handler import CameraHandler, test_camera
from models.face_detection import FaceDetector, demo_face_detection


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='얼굴 인식 프로그램')
    parser.add_argument(
        '--mode',
        type=str,
        choices=['camera', 'face_detection', 'server'],
        default='face_detection',
        help='실행 모드 (camera: 카메라 테스트, face_detection: 얼굴 감지 데모, server: API 서버)'
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

        elif args.mode == 'server':
            print("\n[API 서버 모드]")
            print("API 서버 기능은 아직 구현되지 않았습니다.")
            print("Milestone 4에서 구현 예정")

    except KeyboardInterrupt:
        print("\n프로그램을 종료합니다.")
    except Exception as e:
        print(f"\n오류 발생: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
