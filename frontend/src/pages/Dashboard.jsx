import { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { faceAPI } from '../services/api';

function Dashboard() {
  const { t } = useTranslation();
  const isDemo = new URLSearchParams(window.location.search).has('demo');
  const previewRef = useRef(null);
  const previewStreamRef = useRef(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState({
    faces_detected: 0,
    faces_recognized: 0,
    fps: 0,
    recognized_faces: []
  });
  const streamUrl = faceAPI.getCameraStreamUrl();

  // Electron demo mode intentionally uses the device camera directly. It is a
  // UI/permission check only and does not invoke the CUDA-backed API.
  useEffect(() => {
    if (!isDemo) return undefined;

    let cancelled = false;

    const startLocalPreview = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: 'user' },
          audio: false,
        });

        if (cancelled) {
          stream.getTracks().forEach((track) => track.stop());
          return;
        }

        previewStreamRef.current = stream;
        if (previewRef.current) {
          previewRef.current.srcObject = stream;
          await previewRef.current.play();
        }
        setIsStreaming(true);
        setError(null);
      } catch (cameraError) {
        console.error('Demo camera preview failed:', cameraError);
        setError(t('dashboard.demo.cameraError'));
        setIsStreaming(false);
      }
    };

    startLocalPreview();

    return () => {
      cancelled = true;
      previewStreamRef.current?.getTracks().forEach((track) => track.stop());
      previewStreamRef.current = null;
    };
  }, [isDemo, t]);

  // 컴포넌트 마운트 시 백엔드 카메라 재시작
  useEffect(() => {
    if (isDemo) return undefined;

    const startBackendCamera = async () => {
      try {
        await faceAPI.reopenCamera();
        console.log('백엔드 카메라가 시작되었습니다.');
      } catch (error) {
        console.warn('백엔드 카메라 시작 실패:', error.message);
      }
    };

    startBackendCamera();
  }, [isDemo]);

  // 실시간 통계 업데이트
  useEffect(() => {
    let intervalId = null;

    const fetchStats = async () => {
      try {
        const response = await faceAPI.getCameraStats();
        setStats({
          faces_detected: response.data.faces_detected,
          faces_recognized: response.data.faces_recognized,
          fps: response.data.fps,
          recognized_faces: response.data.recognized_faces || []
        });
      } catch (error) {
        // 통계 가져오기 실패 시 무시 (스트림이 시작되지 않았을 수 있음)
        console.debug('Stats fetch failed:', error.message);
      }
    };

    // 스트리밍 중일 때만 통계 업데이트
    if (isStreaming && !isDemo) {
      // 즉시 한 번 실행
      fetchStats();

      // 1초마다 통계 업데이트
      intervalId = setInterval(fetchStats, 1000);
    }

    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [isDemo, isStreaming]);

  const handleStreamError = () => {
    setError(t('dashboard.error'));
    setIsStreaming(false);
  };

  const handleStreamLoad = () => {
    setIsStreaming(true);
    setError(null);
  };

  return (
    <div className="space-y-4 sm:space-y-6">
      <div>
        <h2 className="text-2xl sm:text-3xl font-bold text-gray-800">{t('dashboard.title')}</h2>
        <p className="text-sm sm:text-base text-gray-600 mt-1 sm:mt-2">{t('dashboard.subtitle')}</p>
      </div>

      <div className="bg-white rounded-lg shadow-md p-3 sm:p-6">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xl font-semibold text-gray-800">{t('dashboard.cameraFeed')}</h3>
            <div className="flex items-center space-x-2">
              <div
                className={`w-3 h-3 rounded-full ${
                  isStreaming ? 'bg-green-500 animate-pulse' : 'bg-red-500'
                }`}
              ></div>
              <span className="text-sm font-medium text-gray-700">
                {isStreaming ? t('dashboard.live') : t('dashboard.offline')}
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
                    {t('dashboard.retry')}
                  </button>
                </div>
              </div>
            ) : isDemo ? (
              <>
                <video
                  ref={previewRef}
                  autoPlay
                  muted
                  playsInline
                  className="w-full h-full object-contain"
                />
                <div className="absolute top-3 left-3 rounded bg-amber-500 px-3 py-1 text-xs font-bold tracking-wide text-white shadow">
                  {t('dashboard.demo.badge')}
                </div>
              </>
            ) : (
              <img
                src={streamUrl}
                alt="Camera Stream"
                className="w-full h-full object-contain"
                onError={handleStreamError}
                onLoad={handleStreamLoad}
              />
            )}
            {isStreaming && !error && stats.recognized_faces.length > 0 && (
              <div
                data-testid="face-info-overlay"
                className="absolute inset-x-0 bottom-0 h-1/5 flex items-center gap-2 sm:gap-4 bg-black/50 px-2 sm:px-4 text-white"
              >
                <h3 className="shrink-0 text-[10px] sm:text-sm font-semibold">
                  {t('dashboard.faceInfo.title')}
                </h3>
                <div className="flex h-full min-w-0 flex-1 items-center gap-2 sm:gap-3 overflow-x-auto">
                  {stats.recognized_faces.map((face, index) => (
                    <div
                      key={index}
                      className={`flex shrink-0 items-center gap-2 border-l-2 pl-2 sm:pl-3 ${
                        face.name === 'Unknown' ? 'border-red-400' : 'border-green-400'
                      }`}
                    >
                      <span className="text-xs sm:text-xl font-bold">
                        {face.name === 'Unknown' ? t('dashboard.faceInfo.unknown') : face.name}
                      </span>
                      {face.confidence != null && (
                        <span className="text-[10px] sm:text-sm text-white/80">
                          {Math.round(face.confidence * 100)}%
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="grid grid-cols-3 gap-2 sm:gap-4 mt-4 sm:mt-6">
            <div className="bg-blue-50 rounded-lg p-2 sm:p-4">
              <div className="flex flex-col sm:flex-row items-center sm:space-x-3 text-center sm:text-left">
                <div className="w-8 h-8 sm:w-12 sm:h-12 bg-blue-500 rounded-full flex items-center justify-center flex-shrink-0 mb-1 sm:mb-0">
                  <svg
                    className="w-4 h-4 sm:w-6 sm:h-6 text-white"
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
                  <p className="text-xs sm:text-sm text-gray-600">{t('dashboard.stats.detected')}</p>
                  <p className="text-lg sm:text-2xl font-bold text-gray-800">
                    {isStreaming ? stats.faces_detected : '-'}
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-green-50 rounded-lg p-2 sm:p-4">
              <div className="flex flex-col sm:flex-row items-center sm:space-x-3 text-center sm:text-left">
                <div className="w-8 h-8 sm:w-12 sm:h-12 bg-green-500 rounded-full flex items-center justify-center flex-shrink-0 mb-1 sm:mb-0">
                  <svg
                    className="w-4 h-4 sm:w-6 sm:h-6 text-white"
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
                  <p className="text-xs sm:text-sm text-gray-600">{t('dashboard.stats.recognized')}</p>
                  <p className="text-lg sm:text-2xl font-bold text-gray-800">
                    {isStreaming ? stats.faces_recognized : '-'}
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-purple-50 rounded-lg p-2 sm:p-4">
              <div className="flex flex-col sm:flex-row items-center sm:space-x-3 text-center sm:text-left">
                <div className="w-8 h-8 sm:w-12 sm:h-12 bg-purple-500 rounded-full flex items-center justify-center flex-shrink-0 mb-1 sm:mb-0">
                  <svg
                    className="w-4 h-4 sm:w-6 sm:h-6 text-white"
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
                  <p className="text-xs sm:text-sm text-gray-600">{t('dashboard.stats.fps')}</p>
                  <p className="text-lg sm:text-2xl font-bold text-gray-800">
                    {isStreaming ? `${stats.fps}` : '-'}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {isDemo && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 sm:p-4 text-sm text-amber-900">
          <span className="font-semibold">{t('dashboard.demo.title')}</span>{' '}
          {t('dashboard.demo.description')}
        </div>
      )}

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 sm:p-4 hidden sm:block">
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
            <h4 className="font-semibold text-blue-800">{t('dashboard.info.title')}</h4>
            <p className="text-sm text-blue-700 mt-1">
              {t('dashboard.info.description')}
              <br />
              <code className="bg-blue-100 px-2 py-1 rounded">{t('dashboard.info.serverCommand')}</code>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
