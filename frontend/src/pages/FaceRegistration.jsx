import { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { faceAPI } from '../services/api';

function FaceRegistration() {
  const { t } = useTranslation();
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);

  const [cameraActive, setCameraActive] = useState(false);
  const [captured, setCaptured] = useState(null);
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });
  const [step, setStep] = useState('camera'); // 'camera', 'captured', 'registered'

  // 카메라 시작
  const startCamera = async () => {
    try {
      // 먼저 카메라를 활성화하여 video 엘리먼트가 렌더링되도록 함
      setCameraActive(true);
      setStep('camera');
      setMessage({ type: '', text: '' });

      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480 }
      });

      // video 엘리먼트가 렌더링될 때까지 잠시 대기
      await new Promise(resolve => setTimeout(resolve, 100));

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        streamRef.current = stream;
      } else {
        // videoRef가 없으면 카메라 비활성화
        stream.getTracks().forEach(track => track.stop());
        setCameraActive(false);
        setMessage({
          type: 'error',
          text: '비디오 엘리먼트를 초기화할 수 없습니다.'
        });
      }
    } catch (error) {
      console.error('카메라 접근 오류:', error);
      setCameraActive(false);
      setMessage({
        type: 'error',
        text: '카메라에 접근할 수 없습니다. 권한을 확인해주세요.'
      });
    }
  };

  // 카메라 중지
  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setCameraActive(false);
  };

  // 이미지 캡처
  const captureImage = () => {
    if (!videoRef.current || !canvasRef.current) return;

    const video = videoRef.current;
    const canvas = canvasRef.current;
    const context = canvas.getContext('2d');

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    // 캔버스에 비디오 프레임 그리기
    context.drawImage(video, 0, 0, canvas.width, canvas.height);

    // 이미지 데이터 URL로 변환
    const imageDataUrl = canvas.toDataURL('image/jpeg', 0.9);
    setCaptured(imageDataUrl);
    setStep('captured');
    stopCamera();
  };

  // 다시 촬영
  const retake = () => {
    setCaptured(null);
    setName('');
    setMessage({ type: '', text: '' });
    startCamera();
  };

  // 등록
  const handleRegister = async () => {
    console.log('=== 얼굴 등록 시작 ===');

    if (!name.trim()) {
      setMessage({ type: 'error', text: t('registration.messages.enterName') });
      return;
    }

    if (!captured) {
      setMessage({ type: 'error', text: t('registration.messages.captureFirst') });
      return;
    }

    setLoading(true);
    setMessage({ type: '', text: '' });

    try {
      console.log('캡처된 이미지 변환 중...');

      // Data URL을 Blob으로 변환
      const blob = await (await fetch(captured)).blob();
      const file = new File([blob], 'captured.jpg', { type: 'image/jpeg' });

      console.log('FormData 생성 중...', { name, fileSize: file.size });

      const formData = new FormData();
      formData.append('name', name);
      formData.append('file', file);

      console.log('API 호출 중...');
      const response = await faceAPI.registerFace(formData);

      console.log('API 응답:', response.data);

      if (response.data.success) {
        console.log('등록 성공!');
        setMessage({
          type: 'success',
          text: response.data.message || `${name}님의 얼굴이 성공적으로 등록되었습니다!`
        });
        setStep('registered');

        // 3초 후 초기화
        setTimeout(() => {
          setCaptured(null);
          setName('');
          setMessage({ type: '', text: '' });
          setStep('camera');
        }, 3000);
      } else {
        console.warn('등록 실패:', response.data.message);
        setMessage({
          type: 'error',
          text: response.data.message || '얼굴 등록에 실패했습니다.'
        });
      }
    } catch (error) {
      console.error('=== 등록 오류 발생 ===');
      console.error('오류 상세:', error);
      console.error('오류 응답:', error.response);

      let errorMessage = '얼굴 등록에 실패했습니다. 다시 시도해주세요.';

      if (error.response) {
        // 서버가 응답했지만 오류 상태 코드
        const detail = error.response.data?.detail;
        const message = error.response.data?.message;

        if (Array.isArray(detail)) {
          // FastAPI 유효성 검사 에러 (422)
          errorMessage = detail.map(err => err.msg || JSON.stringify(err)).join(', ');
        } else if (typeof detail === 'string') {
          errorMessage = detail;
        } else if (message) {
          errorMessage = message;
        }

        console.error('서버 오류 응답:', error.response.status, error.response.data);
      } else if (error.request) {
        // 요청이 전송되었지만 응답을 받지 못함
        errorMessage = '서버에 연결할 수 없습니다. 백엔드 서버가 실행 중인지 확인해주세요.';
        console.error('서버 응답 없음:', error.request);
      } else {
        // 요청 설정 중 오류 발생
        errorMessage = `요청 오류: ${error.message}`;
        console.error('요청 설정 오류:', error.message);
      }

      setMessage({
        type: 'error',
        text: errorMessage
      });
    } finally {
      console.log('로딩 상태 해제');
      setLoading(false);
    }
  };

  // 키보드 이벤트 (스페이스바로 캡처)
  useEffect(() => {
    const handleKeyPress = (e) => {
      if (e.code === 'Space' && cameraActive && step === 'camera') {
        e.preventDefault();
        captureImage();
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [cameraActive, step]);

  // 컴포넌트 언마운트 시 카메라 중지
  useEffect(() => {
    return () => {
      stopCamera();
    };
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-gray-800">{t('registration.title')}</h2>
        <p className="text-gray-600 mt-2">{t('registration.subtitle')}</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 카메라/캡처 영역 */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="aspect-video bg-gray-900 rounded-lg overflow-hidden relative">
              {!cameraActive && !captured && (
                <div className="absolute inset-0 flex items-center justify-center">
                  <button
                    onClick={startCamera}
                    className="px-8 py-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center space-x-3"
                  >
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
                      />
                    </svg>
                    <span className="text-lg font-medium">{t('registration.startCamera')}</span>
                  </button>
                </div>
              )}

              {cameraActive && (
                <>
                  <video
                    ref={videoRef}
                    autoPlay
                    playsInline
                    className="w-full h-full object-cover"
                  />
                  <canvas ref={canvasRef} className="hidden" />
                  <div className="absolute bottom-4 left-0 right-0 flex justify-center space-x-4">
                    <button
                      onClick={captureImage}
                      className="px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors flex items-center space-x-2 shadow-lg"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"
                        />
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M15 13a3 3 0 11-6 0 3 3 0 016 0z"
                        />
                      </svg>
                      <span>{t('registration.capture')}</span>
                    </button>
                    <button
                      onClick={stopCamera}
                      className="px-6 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors flex items-center space-x-2 shadow-lg"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M6 18L18 6M6 6l12 12"
                        />
                      </svg>
                      <span>{t('registration.stopCamera')}</span>
                    </button>
                  </div>
                </>
              )}

              {captured && (
                <>
                  <img src={captured} alt="Captured" className="w-full h-full object-cover" />
                  {step === 'captured' && (
                    <div className="absolute bottom-4 left-0 right-0 flex justify-center">
                      <button
                        onClick={retake}
                        className="px-6 py-3 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 transition-colors flex items-center space-x-2 shadow-lg"
                      >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                          />
                        </svg>
                        <span>{t('registration.retake')}</span>
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>

            {cameraActive && (
              <div className="mt-4 bg-blue-50 border border-blue-200 rounded-lg p-3">
                <div className="flex items-start space-x-2">
                  <svg
                    className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5"
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
                    <p className="text-sm font-medium text-blue-800">{t('registration.captureGuide.title')}</p>
                    <ul className="text-sm text-blue-700 mt-1 space-y-1">
                      <li>• {t('registration.captureGuide.face')}</li>
                      <li>• {t('registration.captureGuide.lighting')}</li>
                      <li>• {t('registration.captureGuide.distance')}</li>
                      <li>• {t('registration.captureGuide.expression')}</li>
                    </ul>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* 등록 정보 입력 */}
        <div className="space-y-6">
          <div className="bg-white rounded-lg shadow-md p-6">
            <h3 className="text-xl font-semibold text-gray-800 mb-4">{t('registration.info.title')}</h3>

            {step === 'registered' ? (
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <div className="flex items-center space-x-3">
                  <svg
                    className="w-8 h-8 text-green-600"
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
                  <div>
                    <h4 className="font-semibold text-green-800">{t('registration.messages.success')}</h4>
                    <p className="text-sm text-green-700 mt-1">{t('registration.messages.starting')}</p>
                  </div>
                </div>
              </div>
            ) : (
              <>
                <div className="space-y-4">
                  <div>
                    <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-2">
                      {t('registration.name')}
                    </label>
                    <input
                      type="text"
                      id="name"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder={t('registration.namePlaceholder')}
                      disabled={loading || !captured}
                    />
                  </div>

                  {message.text && (
                    <div
                      className={`p-3 rounded-lg text-sm ${
                        message.type === 'success'
                          ? 'bg-green-50 text-green-800 border border-green-200'
                          : 'bg-red-50 text-red-800 border border-red-200'
                      }`}
                    >
                      <div className="flex items-center space-x-2">
                        {message.type === 'success' ? (
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          </svg>
                        ) : (
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        )}
                        <span className="font-medium">{message.text}</span>
                      </div>
                    </div>
                  )}

                  <button
                    onClick={handleRegister}
                    disabled={loading || !captured || !name.trim()}
                    className={`w-full py-3 px-4 rounded-lg text-white font-medium transition-colors ${
                      loading || !captured || !name.trim()
                        ? 'bg-gray-400 cursor-not-allowed'
                        : 'bg-blue-600 hover:bg-blue-700'
                    }`}
                  >
                    {loading ? (
                      <span className="flex items-center justify-center">
                        <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                          <circle
                            className="opacity-25"
                            cx="12"
                            cy="12"
                            r="10"
                            stroke="currentColor"
                            strokeWidth="4"
                          ></circle>
                          <path
                            className="opacity-75"
                            fill="currentColor"
                            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                          ></path>
                        </svg>
                        {t('registration.registering')}
                      </span>
                    ) : (
                      t('registration.register')
                    )}
                  </button>
                </div>
              </>
            )}
          </div>

          {/* 등록 절차 안내 */}
          <div className="bg-gray-50 rounded-lg shadow-md p-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-3">{t('registration.steps.title')}</h3>
            <div className="space-y-3">
              <div className="flex items-start space-x-3">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                    cameraActive || captured ? 'bg-green-500 text-white' : 'bg-gray-300 text-gray-600'
                  }`}
                >
                  1
                </div>
                <div className="flex-1">
                  <p className="font-medium text-gray-800">{t('registration.steps.camera')}</p>
                  <p className="text-sm text-gray-600">{t('registration.captureGuide.face')}</p>
                </div>
              </div>

              <div className="flex items-start space-x-3">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                    captured ? 'bg-green-500 text-white' : 'bg-gray-300 text-gray-600'
                  }`}
                >
                  2
                </div>
                <div className="flex-1">
                  <p className="font-medium text-gray-800">{t('registration.steps.capture')}</p>
                  <p className="text-sm text-gray-600">{t('registration.captureGuide.expression')}</p>
                </div>
              </div>

              <div className="flex items-start space-x-3">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                    name.trim() && captured ? 'bg-green-500 text-white' : 'bg-gray-300 text-gray-600'
                  }`}
                >
                  3
                </div>
                <div className="flex-1">
                  <p className="font-medium text-gray-800">{t('registration.steps.name')}</p>
                  <p className="text-sm text-gray-600">{t('registration.info.description')}</p>
                </div>
              </div>

              <div className="flex items-start space-x-3">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                    step === 'registered' ? 'bg-green-500 text-white' : 'bg-gray-300 text-gray-600'
                  }`}
                >
                  4
                </div>
                <div className="flex-1">
                  <p className="font-medium text-gray-800">{t('registration.steps.complete')}</p>
                  <p className="text-sm text-gray-600">{t('registration.register')}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default FaceRegistration;
