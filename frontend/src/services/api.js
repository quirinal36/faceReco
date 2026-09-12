import axios from 'axios';
import { clearAuth, getStoredToken } from '../auth/session';

// The URL is public configuration only. Credentials are always supplied at runtime.
const API_BASE_URL = import.meta.env.VITE_API_URL || '';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
});

api.interceptors.request.use((config) => {
  const token = getStoredToken();

  if (token && !config.headers.has('Authorization')) {
    config.headers.set('Authorization', `Bearer ${token}`);
  }

  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      clearAuth();
    }
    return Promise.reject(error);
  },
);

export const getHttpStatus = (error) => error?.response?.status ?? null;

export const getApiUrl = (path) => {
  if (!API_BASE_URL) return path;
  return `${API_BASE_URL.replace(/\/$/, '')}${path}`;
};

export const authAPI = {
  whoami: (token) => api.get('/api/auth/whoami', {
    headers: { Authorization: `Bearer ${token}` },
  }),
};

export const eduAPI = {
  getStudents: (query = '') => api.get('/api/edu/students', { params: query ? { q: query } : {} }),
  getEnrollments: (month) => api.get('/api/edu/enrollments', { params: { month } }),
};

export const faceAPI = {
  getFaces: () => api.get('/api/faces/list'),

  getFaceThumbnail: (faceId, signal) => api.get(
    `/api/faces/${encodeURIComponent(faceId)}/thumbnail`,
    { responseType: 'blob', signal },
  ),

  registerFace: (formData) => api.post('/api/face/register', formData),

  deleteFace: (id) => api.delete(`/api/face/${encodeURIComponent(id)}`),

  addFaceSample: (faceId, formData) => api.post(
    `/api/face/${encodeURIComponent(faceId)}/add-sample`,
    formData,
  ),

  mergeFacesByName: (name) => api.post('/api/faces/merge', { name }),

  getCameraStats: () => api.get('/api/camera/stats'),

  releaseCamera: () => api.post('/api/camera/release'),

  reopenCamera: () => api.post('/api/camera/reopen'),

  getAttendanceToday: () => api.get('/api/attendance/today'),

  getAttendanceByDate: (date) => api.get(`/api/attendance/date/${date}`),

  getAttendanceRange: (startDate, endDate) => api.get('/api/attendance/range', {
    params: { start_date: startDate, end_date: endDate },
  }),

  getAttendanceByPerson: (name, startDate, endDate) => api.post(
    '/api/attendance/person/search',
    {
      name,
      start_date: startDate || null,
      end_date: endDate || null,
    },
  ),

  getAttendanceStats: (startDate, endDate) => api.get('/api/attendance/stats', {
    params: { start_date: startDate, end_date: endDate },
  }),

  deleteAttendance: (id) => api.delete(`/api/attendance/${encodeURIComponent(id)}`),

  startLivenessSession: () => api.post('/api/liveness/start'),

  checkLiveness: (sessionId, imageBlob) => {
    const formData = new FormData();
    formData.append('session_id', sessionId);
    formData.append('file', imageBlob, 'frame.jpg');
    return api.post('/api/liveness/check', formData);
  },

  getLivenessStatus: (sessionId) => api.post('/api/liveness/status', {
    session_id: sessionId,
  }),
};

export default api;
