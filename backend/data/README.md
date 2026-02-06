# 얼굴 데이터베이스 디렉토리

이 디렉토리는 얼굴 인식 시스템의 데이터를 저장합니다.

## 디렉토리 구조

```
data/
├── face_database.json     # 얼굴 메타데이터 (이름, 등록일 등)
├── embeddings/            # 얼굴 임베딩 벡터 (.npy 파일, 512차원)
│   └── person_*.npy
└── faces/                 # 얼굴 이미지 (참조용)
    └── person_*.jpg
```

## 주의사항

- 이 디렉토리의 실제 데이터 파일(.json, .npy, .jpg)은 Git에 커밋되지 않습니다 (개인정보 보호)
- 디렉토리 구조만 유지됩니다
- 첫 얼굴 등록 시 자동으로 파일이 생성됩니다

## 사용법

```bash
# 얼굴 등록
python app.py --mode register --camera-id 0

# 얼굴 인식
python app.py --mode face_recognition --camera-id 0
```

## 백업

중요한 데이터는 별도로 백업하세요:
```bash
# 전체 data 디렉토리 백업
tar -czf face_data_backup_$(date +%Y%m%d).tar.gz data/
```
