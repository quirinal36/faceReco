import { useState, useEffect } from 'react';
import { faceAPI } from '../services/api';

function Dashboard() {
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState(null);
  const streamUrl = faceAPI.getCameraStreamUrl();

  const handleStreamError = () => {
    setError('카메라 스트림을 불러올 수 없습니다. 백엔드 서버가 실행 중인지 확인하세요.');
    setIsStreaming(false);
  };

  const handleStreamLoad = () => {
    setIsStreaming(true);
    setError(null);
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-gray-800">실시간 카메라 모니터링</h2>
        <p className="text-gray-600 mt-2">얼굴 인식 시스템의 실시간 피드를 확인하세요</p>
      </div>

      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xl font-semibold text-gray-800">카메라 피드</h3>
            <div className="flex items-center space-x-2">
              <div
                className={`w-3 h-3 rounded-full ${
                  isStreaming ? 'bg-green-500 animate-pulse' : 'bg-red-500'
                }`}
              ></div>
              <span className="text-sm font-medium text-gray-700">
                {isStreaming ? 'LIVE' : 'OFFLINE'}
              </span>
            </div>
          </div>

          <div className="relative bg-gray-900 rounded-lg overflow-hidden aspect-video">
            {error ? (
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="text-center space-y-3">
                  <svg
                    className="w-16 h-16 text-red-400 mx-auto"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                  <p className="text-white">{error}</p>
                  <button
                    onClick={() => window.location.reload()}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    다시 시도
                  </button>
                </div>
              </div>
            ) : (
              <img
                src={streamUrl}
                alt="Camera Stream"
                className="w-full h-full object-contain"
                onError={handleStreamError}
                onLoad={handleStreamLoad}
              />
            )}
          </div>

          <div className="grid grid-cols-3 gap-4 mt-6">
            <div className="bg-blue-50 rounded-lg p-4">
              <div className="flex items-center space-x-3">
                <div className="w-12 h-12 bg-blue-500 rounded-full flex items-center justify-center">
                  <svg
                    className="w-6 h-6 text-white"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                    />
                  </svg>
                </div>
                <div>
                  <p className="text-sm text-gray-600">감지된 얼굴</p>
                  <p className="text-2xl font-bold text-gray-800">-</p>
                </div>
              </div>
            </div>

            <div className="bg-green-50 rounded-lg p-4">
              <div className="flex items-center space-x-3">
                <div className="w-12 h-12 bg-green-500 rounded-full flex items-center justify-center">
                  <svg
                    className="w-6 h-6 text-white"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                </div>
                <div>
                  <p className="text-sm text-gray-600">인식 성공</p>
                  <p className="text-2xl font-bold text-gray-800">-</p>
                </div>
              </div>
            </div>

            <div className="bg-purple-50 rounded-lg p-4">
              <div className="flex items-center space-x-3">
                <div className="w-12 h-12 bg-purple-500 rounded-full flex items-center justify-center">
                  <svg
                    className="w-6 h-6 text-white"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                </div>
                <div>
                  <p className="text-sm text-gray-600">처리 속도</p>
                  <p className="text-2xl font-bold text-gray-800">- FPS</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start space-x-3">
          <svg
            className="w-6 h-6 text-blue-600 flex-shrink-0 mt-0.5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <div>
            <h4 className="font-semibold text-blue-800">시스템 안내</h4>
            <p className="text-sm text-blue-700 mt-1">
              실시간 카메라 피드가 표시되지 않는 경우, 백엔드 서버가 실행 중인지 확인하세요.
              <br />
              서버 실행: <code className="bg-blue-100 px-2 py-1 rounded">cd backend && python server.py</code>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
