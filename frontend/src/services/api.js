import axios from 'axios';

// API 기본 URL (백엔드 서버 주소)
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Axios 인스턴스 생성
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 요청 인터셉터
api.interceptors.request.use(
  (config) => {
    // 여기에 토큰이나 다른 헤더를 추가할 수 있습니다
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 응답 인터셉터
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    // 에러 처리
    if (error.response) {
      // 서버가 응답을 반환했지만 상태 코드가 2xx가 아닌 경우
      console.error('Error response:', error.response.data);
    } else if (error.request) {
      // 요청이 전송되었지만 응답을 받지 못한 경우
      console.error('No response received:', error.request);
    } else {
      // 요청 설정 중에 오류가 발생한 경우
      console.error('Error setting up request:', error.message);
    }
    return Promise.reject(error);
  }
);

// API 함수들
export const faceAPI = {
  // 얼굴 목록 조회
  getFaces: () => api.get('/api/faces/list'),

  // 얼굴 등록
  registerFace: (formData) => api.post('/api/face/register', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  }),

  // 얼굴 삭제
  deleteFace: (id) => api.delete(`/api/face/${id}`),

  // 얼굴 인식
  recognizeFace: (formData) => api.post('/api/face/recognize', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  }),

  // 카메라 스트림 URL
  getCameraStreamUrl: () => `${API_BASE_URL}/api/camera/stream`,
};

export default api;
