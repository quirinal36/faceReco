"""
이미지 파일로 얼굴 인식 테스트

WSL 환경에서 카메라 접근이 어려울 때 사용
"""

import cv2
import sys
from models.face_recognition import FaceRecognizer
from models.face_database import FaceDatabase


def test_registration_from_image(image_path: str, name: str):
    """
    이미지 파일로 얼굴 등록 테스트

    Args:
        image_path (str): 얼굴 이미지 경로
        name (str): 등록할 이름
    """
    print(f"이미지에서 얼굴 등록 중: {image_path}")

    # 이미지 로드
    image = cv2.imread(image_path)
    if image is None:
        print(f"이미지를 로드할 수 없습니다: {image_path}")
        return

    # 얼굴 인식기 및 데이터베이스 초기화
    recognizer = FaceRecognizer()
    database = FaceDatabase()

    # 임베딩 추출
    embedding = recognizer.extract_embedding(image)

    if embedding is not None:
        import datetime
        face_id = f"person_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"

        metadata = {
            'name': name,
            'registered_at': datetime.datetime.now().isoformat(),
            'source': 'image_file'
        }

        success = database.register_face(face_id, embedding, metadata, image)

        if success:
            print(f"✓ 등록 완료: {name} (ID: {face_id})")
            print(f"  - 임베딩 크기: {embedding.shape}")
        else:
            print(f"✗ 등록 실패")
    else:
        print("✗ 얼굴을 감지할 수 없습니다")


def test_recognition_from_image(image_path: str):
    """
    이미지 파일로 얼굴 인식 테스트

    Args:
        image_path (str): 테스트할 얼굴 이미지 경로
    """
    print(f"이미지에서 얼굴 인식 중: {image_path}")

    # 이미지 로드
    image = cv2.imread(image_path)
    if image is None:
        print(f"이미지를 로드할 수 없습니다: {image_path}")
        return

    # 얼굴 인식기 및 데이터베이스 초기화
    recognizer = FaceRecognizer()
    database = FaceDatabase()

    print(f"데이터베이스: {len(database)}명 등록됨")

    # 모든 얼굴 감지 및 인식
    results = recognizer.detect_and_extract(image)

    if len(results) == 0:
        print("✗ 얼굴을 감지할 수 없습니다")
        return

    print(f"✓ {len(results)}개의 얼굴 감지됨")

    for i, (bbox, embedding) in enumerate(results):
        x1, y1, x2, y2 = bbox

        # 데이터베이스에서 매칭
        match = database.recognize_face(embedding)

        if match:
            face_id, confidence = match
            face_data = database.faces.get(face_id)
            name = face_data['metadata'].get('name', 'Unknown') if face_data else 'Unknown'

            print(f"  [{i+1}] 인식: {name} (신뢰도: {confidence:.3f})")

            # 녹색 박스
            cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
            label = f"{name} ({confidence:.2f})"
        else:
            print(f"  [{i+1}] 미등록 얼굴")

            # 빨간색 박스
            cv2.rectangle(image, (x1, y1), (x2, y2), (0, 0, 255), 2)
            label = "Unknown"

        # 레이블 추가
        cv2.putText(image, label, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (255, 255, 255), 2)

    # 결과 이미지 저장
    output_path = image_path.replace('.jpg', '_result.jpg').replace('.png', '_result.png')
    cv2.imwrite(output_path, image)
    print(f"\n결과 이미지 저장: {output_path}")


def main():
    """메인 함수"""
    if len(sys.argv) < 3:
        print("사용법:")
        print("  얼굴 등록: python test_with_image.py register <이미지경로> <이름>")
        print("  얼굴 인식: python test_with_image.py recognize <이미지경로>")
        print()
        print("예시:")
        print("  python test_with_image.py register photo1.jpg '홍길동'")
        print("  python test_with_image.py recognize photo2.jpg")
        return

    mode = sys.argv[1]
    image_path = sys.argv[2]

    try:
        if mode == 'register':
            if len(sys.argv) < 4:
                print("이름을 입력하세요")
                return
            name = sys.argv[3]
            test_registration_from_image(image_path, name)

        elif mode == 'recognize':
            test_recognition_from_image(image_path)

        else:
            print(f"알 수 없는 모드: {mode}")
            print("'register' 또는 'recognize'를 사용하세요")

    except Exception as e:
        print(f"오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
