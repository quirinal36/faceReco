# 얼굴 인식 프로그램 작성

## 구현 현황 (2026-08-19)

- [x] 로컬 CUDA GPU 기반 InsightFace 얼굴 인식 및 실시간 카메라 처리
- [x] operator/device 역할 분리와 인증된 웹 대시보드
- [x] 최소 얼굴 썸네일·private storage·업로드 제한으로 원본 생체정보 노출 방지
- [x] Edu Manager REST API를 통한 학생 선택과 월별 수강행 출석 기록
- [ ] Jetson 운영 런타임에서 CUDA/TensorRT wheel 설치 후 end-to-end 성능 검증
- [ ] 기존 얼굴 데이터의 학생/수강행 연결 마이그레이션
- [ ] 보안 운영 승인 및 공개 Git 이력 노출 사고 대응 완료

1. Camera 연동 
2. Machine Learning 이용 
- Hugging face 에서 모델 찾아서 활용
3. 파이썬 언어를 활용
4. 웹 대시보드 작성까지
5. github 사용, github issues 에 문서화 마일스톤
