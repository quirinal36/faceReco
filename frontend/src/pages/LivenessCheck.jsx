import { useState, useRef, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { faceAPI } from '../services/api';

/**
 * 타원 위의 각도(degree)를 Canvas 좌표로 변환
 * @param {number} angle - 0~360도 (0=우측, 90=상단, 180=좌측, 270=하단)
 * @param {number} cx - 타원 중심 X
 * @param {number} cy - 타원 중심 Y
 * @param {number} rx - 타원 반지름 X
 * @param {number} ry - 타원 반지름 Y
 */
function ellipsePoint(angle, cx, cy, rx, ry) {
  const rad = (angle * Math.PI) / 180;
  return {
    x: cx + rx * Math.cos(rad),
    y: cy - ry * Math.sin(rad), // Canvas Y축은 아래로 증가
  };
}

function LivenessCheck() {
  const { t } = useTranslation();
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const overlayCanvasRef = useRef(null);
  const streamRef = useRef(null);
  const checkIntervalRef = useRef(null);

  // 상태
  const [cameraActive, setCameraActive] = useState(false);
  const [session, setSession] = useState(null);
  const [currentChallenge, setCurrentChallenge] = useState(null);
  const [status, setStatus] = useState('idle'); // idle, starting, challenging, passed, failed, expired
  const [message, setMessage] = useState('');
  const [lastResult, setLastResult] = useState(null);
  const [faceName, setFaceName] = useState(null);
  const [faceConfidence, setFaceConfidence] = useState(null);
  const [timeLeft, setTimeLeft] = useState(0);
  const [passedCount, setPassedCount] = useState(0);

  // 카메라 시작
  const startCamera = async () => {
    try {
      // 백엔드 카메라 해제
      await faceAPI.releaseCamera().catch(() => {});

      setCameraActive(true);
      setMessage(t('liveness.messages.startingCamera'));

      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 640 },
          height: { ideal: 480 },
          facingMode: 'user',
        },
      });

      await new Promise((resolve) => setTimeout(resolve, 100));

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        streamRef.current = stream;
      } else {
        stream.getTracks().forEach((track) => track.stop());
        setCameraActive(false);
      }
    } catch (error) {
      console.error('카메라 접근 오류:', error);
      setCameraActive(false);
      setMessage(t('liveness.messages.cameraError'));
    }
  };

  // 카메라 중지
  const stopCamera = useCallback(() => {
    if (checkIntervalRef.current) {
      clearInterval(checkIntervalRef.current);
      checkIntervalRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setCameraActive(false);
  }, []);

  // 세션 시작
  const startSession = async () => {
    try {
      setStatus('starting');
      setMessage(t('liveness.messages.creatingSession'));
      setPassedCount(0);
      setFaceName(null);
      setFaceConfidence(null);
      setLastResult(null);

      if (!cameraActive) {
        await startCamera();
      }

      const response = await faceAPI.startLivenessSession();
      const sessionData = response.data;

      setSession(sessionData);
      setTimeLeft(sessionData.timeout);

      if (sessionData.challenges && sessionData.challenges.length > 0) {
        setCurrentChallenge(sessionData.challenges[0]);
      }

      setStatus('challenging');
      setMessage(t('liveness.messages.turnHead'));
    } catch (error) {
      console.error('세션 시작 실패:', error);
      setStatus('failed');
      if (error.response && error.response.status === 429) {
        setMessage(t('liveness.messages.tooManyRetries'));
      } else {
        setMessage(t('liveness.messages.sessionError'));
      }
    }
  };

  // 프레임 캡처 + 서버 전송
  const captureAndCheck = useCallback(async () => {
    if (!videoRef.current || !canvasRef.current || !session) return;
    if (status !== 'challenging') return;

    const video = videoRef.current;
    const canvas = canvasRef.current;

    if (video.videoWidth === 0 || video.videoHeight === 0) return;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);

    try {
      const blob = await new Promise((resolve) =>
        canvas.toBlob(resolve, 'image/jpeg', 0.8)
      );
      if (!blob) return;

      const response = await faceAPI.checkLiveness(session.session_id, blob);
      const result = response.data;
      setLastResult(result);

      if (result.face_name) {
        setFaceName(result.face_name);
        setFaceConfidence(result.face_confidence);
      }

      if (result.session_completed) {
        setStatus('passed');
        setMessage(t('liveness.messages.passed'));
        setPassedCount(session.total_challenges);
        if (checkIntervalRef.current) {
          clearInterval(checkIntervalRef.current);
          checkIntervalRef.current = null;
        }
      } else if (result.challenge_passed) {
        setPassedCount((prev) => prev + 1);
        // 다음 챌린지로 이동
        if (result.next_target_angle !== null && result.next_target_angle !== undefined) {
          const nextIdx = result.current_challenge_index;
          if (session.challenges && session.challenges[nextIdx]) {
            setCurrentChallenge(session.challenges[nextIdx]);
          }
        }
        setMessage(t('liveness.messages.challengePassed'));
      } else if (result.error === 'session_expired') {
        setStatus('expired');
        setMessage(t('liveness.messages.expired'));
        if (checkIntervalRef.current) {
          clearInterval(checkIntervalRef.current);
          checkIntervalRef.current = null;
        }
      } else if (result.error === 'face_inconsistent') {
        setStatus('failed');
        setMessage(t('liveness.messages.faceChanged'));
        if (checkIntervalRef.current) {
          clearInterval(checkIntervalRef.current);
          checkIntervalRef.current = null;
        }
      } else if (result.error && result.error.startsWith('motion_')) {
        setStatus('failed');
        setMessage(t('liveness.messages.unnaturalMotion'));
        if (checkIntervalRef.current) {
          clearInterval(checkIntervalRef.current);
          checkIntervalRef.current = null;
        }
      } else if (result.error === 'no_face_detected') {
        setMessage(t('liveness.messages.noFace'));
      } else if (result.error === 'no_pose_detected') {
        setMessage(t('liveness.messages.noPose'));
      } else {
        setMessage(t('liveness.messages.turnMore'));
      }
    } catch (error) {
      console.error('Liveness check 오류:', error);
      if (error.response && error.response.status === 429) {
        setStatus('failed');
        setMessage(t('liveness.messages.tooManyRetries'));
        if (checkIntervalRef.current) {
          clearInterval(checkIntervalRef.current);
          checkIntervalRef.current = null;
        }
      }
    }
  }, [session, status, t]);

  // 챌린지 진행 중 주기적 프레임 전송 (500ms 간격)
  useEffect(() => {
    if (status === 'challenging' && session && cameraActive) {
      checkIntervalRef.current = setInterval(captureAndCheck, 500);
      return () => {
        if (checkIntervalRef.current) {
          clearInterval(checkIntervalRef.current);
          checkIntervalRef.current = null;
        }
      };
    }
  }, [status, session, cameraActive, captureAndCheck]);

  // 타이머 카운트다운
  useEffect(() => {
    if (status !== 'challenging' || !session) return;

    const timer = setInterval(() => {
      setTimeLeft((prev) => {
        const next = prev - 1;
        if (next <= 0) {
          setStatus('expired');
          setMessage(t('liveness.messages.expired'));
          clearInterval(timer);
          return 0;
        }
        return next;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [status, session, t]);

  // 오버레이 캔버스에 타원 + 점 그리기
  useEffect(() => {
    const overlay = overlayCanvasRef.current;
    const video = videoRef.current;
    if (!overlay || !video) return;
    if (!cameraActive) return;

    let animId;

    const draw = () => {
      const w = video.videoWidth || 640;
      const h = video.videoHeight || 480;

      // 비디오 표시 크기에 맞추기
      const rect = video.getBoundingClientRect();
      overlay.width = rect.width;
      overlay.height = rect.height;

      const ctx = overlay.getContext('2d');
      ctx.clearRect(0, 0, overlay.width, overlay.height);

      const cx = overlay.width / 2;
      const cy = overlay.height / 2;
      const rx = overlay.width * 0.22;
      const ry = overlay.height * 0.35;

      // 타원 그리기 (얼굴 가이드)
      ctx.beginPath();
      ctx.ellipse(cx, cy, rx, ry, 0, 0, 2 * Math.PI);
      ctx.strokeStyle = status === 'passed'
        ? 'rgba(34, 197, 94, 0.8)'
        : status === 'challenging'
        ? 'rgba(59, 130, 246, 0.8)'
        : 'rgba(156, 163, 175, 0.5)';
      ctx.lineWidth = 3;
      ctx.setLineDash([10, 5]);
      ctx.stroke();
      ctx.setLineDash([]);

      // 현재 챌린지 점(A) 표시
      if (currentChallenge && (status === 'challenging')) {
        const pt = ellipsePoint(currentChallenge.target_angle, cx, cy, rx + 30, ry + 30);

        // 점 외곽 글로우
        ctx.beginPath();
        ctx.arc(pt.x, pt.y, 18, 0, 2 * Math.PI);
        ctx.fillStyle = 'rgba(239, 68, 68, 0.3)';
        ctx.fill();

        // 점
        ctx.beginPath();
        ctx.arc(pt.x, pt.y, 12, 0, 2 * Math.PI);
        ctx.fillStyle = 'rgba(239, 68, 68, 0.9)';
        ctx.fill();

        // 점 안에 화살표 표시 (방향 힌트)
        ctx.fillStyle = 'white';
        ctx.font = 'bold 14px sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('A', pt.x, pt.y);

        // 안내선: 중심 → 점 방향으로 점선
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(pt.x, pt.y);
        ctx.strokeStyle = 'rgba(239, 68, 68, 0.3)';
        ctx.lineWidth = 2;
        ctx.setLineDash([5, 5]);
        ctx.stroke();
        ctx.setLineDash([]);
      }

      // 통과한 챌린지는 녹색 체크 표시
      if (session && session.challenges) {
        session.challenges.forEach((c, i) => {
          if (i < passedCount) {
            const pt = ellipsePoint(c.target_angle, cx, cy, rx + 30, ry + 30);
            ctx.beginPath();
            ctx.arc(pt.x, pt.y, 12, 0, 2 * Math.PI);
            ctx.fillStyle = 'rgba(34, 197, 94, 0.9)';
            ctx.fill();
            ctx.fillStyle = 'white';
            ctx.font = 'bold 14px sans-serif';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText('\u2713', pt.x, pt.y);
          }
        });
      }

      animId = requestAnimationFrame(draw);
    };

    // 비디오 메타데이터 로드 후 시작
    const startDrawing = () => {
      animId = requestAnimationFrame(draw);
    };

    if (video.readyState >= 2) {
      startDrawing();
    } else {
      video.addEventListener('loadeddata', startDrawing, { once: true });
    }

    return () => {
      if (animId) cancelAnimationFrame(animId);
    };
  }, [cameraActive, currentChallenge, session, status, passedCount]);

  // 언마운트 시 정리
  useEffect(() => {
    return () => {
      stopCamera();
      faceAPI.reopenCamera().catch(() => {});
    };
  }, [stopCamera]);

  // 재시도
  const retry = () => {
    setSession(null);
    setCurrentChallenge(null);
    setStatus('idle');
    setMessage('');
    setLastResult(null);
    setFaceName(null);
    setFaceConfidence(null);
    setPassedCount(0);
  };

  // 방향 이름 변환
  const getDirectionLabel = (challenge) => {
    if (!challenge) return '';
    const angle = challenge.target_angle;
    if (angle >= 315 || angle < 45) return t('liveness.directions.right');
    if (angle >= 45 && angle < 135) return t('liveness.directions.up');
    if (angle >= 135 && angle < 225) return t('liveness.directions.left');
    return t('liveness.directions.down');
  };

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* 헤더 */}
      <div>
        <h2 className="text-2xl sm:text-3xl font-bold text-gray-800">
          {t('liveness.title')}
        </h2>
        <p className="text-sm sm:text-base text-gray-600 mt-1 sm:mt-2">
          {t('liveness.subtitle')}
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
        {/* 카메라 영역 */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-lg shadow-md p-3 sm:p-6">
            <div className="aspect-video bg-gray-900 rounded-lg overflow-hidden relative">
              {!cameraActive && status === 'idle' && (
                <div className="absolute inset-0 flex flex-col items-center justify-center space-y-4">
                  <div className="text-center">
                    <svg className="w-16 h-16 text-gray-400 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                        d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                    </svg>
                    <p className="text-gray-400 text-sm mb-4">{t('liveness.messages.ready')}</p>
                  </div>
                  <button
                    onClick={startSession}
                    className="px-8 py-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center space-x-3"
                  >
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                        d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                    </svg>
                    <span className="text-lg font-medium">{t('liveness.startButton')}</span>
                  </button>
                </div>
              )}

              {cameraActive && (
                <>
                  <video
                    ref={videoRef}
                    autoPlay
                    playsInline
                    muted
                    className="w-full h-full object-cover"
                    style={{ transform: 'scaleX(-1)' }}
                  />
                  {/* 오버레이 캔버스 (타원 + 점) */}
                  <canvas
                    ref={overlayCanvasRef}
                    className="absolute inset-0 w-full h-full pointer-events-none"
                    style={{ transform: 'scaleX(-1)' }}
                  />
                  {/* 숨겨진 캡처용 캔버스 */}
                  <canvas ref={canvasRef} className="hidden" />

                  {/* 상단 상태 바 */}
                  <div className="absolute top-3 left-3 right-3 flex justify-between items-center">
                    {/* 타이머 */}
                    {status === 'challenging' && (
                      <div className={`px-3 py-1 rounded-full text-sm font-bold ${
                        timeLeft <= 10 ? 'bg-red-600 text-white' : 'bg-black/50 text-white'
                      }`}>
                        {timeLeft}s
                      </div>
                    )}

                    {/* 진행 상태 */}
                    {session && (
                      <div className="flex space-x-2">
                        {session.challenges.map((_, i) => (
                          <div
                            key={i}
                            className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                              i < passedCount
                                ? 'bg-green-500 text-white'
                                : i === passedCount && status === 'challenging'
                                ? 'bg-blue-500 text-white animate-pulse'
                                : 'bg-white/30 text-white'
                            }`}
                          >
                            {i < passedCount ? '\u2713' : i + 1}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* 하단 메시지 */}
                  <div className="absolute bottom-3 left-3 right-3">
                    <div className={`px-4 py-2 rounded-lg text-center text-sm font-medium ${
                      status === 'passed'
                        ? 'bg-green-600/90 text-white'
                        : status === 'failed' || status === 'expired'
                        ? 'bg-red-600/90 text-white'
                        : 'bg-black/60 text-white'
                    }`}>
                      {message}
                      {status === 'challenging' && currentChallenge && (
                        <span className="block mt-1 text-xs opacity-80">
                          {t('liveness.messages.direction', { direction: getDirectionLabel(currentChallenge) })}
                        </span>
                      )}
                    </div>
                  </div>
                </>
              )}

              {/* 완료/실패 오버레이 */}
              {(status === 'passed' || status === 'failed' || status === 'expired') && cameraActive && (
                <div className="absolute inset-0 bg-black/40 flex items-center justify-center">
                  <div className="bg-white rounded-xl p-6 mx-4 text-center max-w-sm">
                    {status === 'passed' ? (
                      <>
                        <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-3">
                          <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          </svg>
                        </div>
                        <h3 className="text-lg font-bold text-gray-800 mb-1">
                          {t('liveness.result.passedTitle')}
                        </h3>
                        {faceName && (
                          <p className="text-sm text-gray-600 mb-1">
                            {faceName}
                            {faceConfidence && ` (${Math.round(faceConfidence * 100)}%)`}
                          </p>
                        )}
                        <p className="text-sm text-green-600 mb-4">
                          {t('liveness.result.attendanceRecorded')}
                        </p>
                      </>
                    ) : (
                      <>
                        <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-3">
                          <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </div>
                        <h3 className="text-lg font-bold text-gray-800 mb-1">
                          {status === 'expired' ? t('liveness.result.expiredTitle') : t('liveness.result.failedTitle')}
                        </h3>
                        <p className="text-sm text-gray-600 mb-4">
                          {t('liveness.result.tryAgain')}
                        </p>
                      </>
                    )}
                    <button
                      onClick={retry}
                      className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                    >
                      {status === 'passed' ? t('liveness.result.done') : t('liveness.result.retry')}
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Head Pose 디버그 정보 (개발용) */}
            {lastResult && status === 'challenging' && (
              <div className="mt-3 bg-gray-50 rounded-lg p-3 text-xs font-mono text-gray-600">
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    Yaw: <span className="font-bold">{lastResult.measured_yaw ?? '-'}</span>
                    {' '}(target: {lastResult.expected_yaw ?? '-'}, diff: {lastResult.yaw_diff ?? '-'})
                  </div>
                  <div>
                    Pitch: <span className="font-bold">{lastResult.measured_pitch ?? '-'}</span>
                    {' '}(target: {lastResult.expected_pitch ?? '-'}, diff: {lastResult.pitch_diff ?? '-'})
                  </div>
                </div>
                <div className="mt-1 flex items-center space-x-3">
                  <span>Motion Score:</span>
                  <div className="flex-1 bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full transition-all ${
                        (lastResult.motion_score ?? 0) >= 0.3 ? 'bg-green-500' : 'bg-red-400'
                      }`}
                      style={{ width: `${Math.min((lastResult.motion_score ?? 0) * 100, 100)}%` }}
                    />
                  </div>
                  <span className="font-bold">{lastResult.motion_score ?? '-'}</span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* 안내 패널 */}
        <div className="space-y-4 sm:space-y-6">
          {/* 검증 절차 안내 */}
          <div className="bg-white rounded-lg shadow-md p-4 sm:p-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-3">
              {t('liveness.guide.title')}
            </h3>
            <div className="space-y-3">
              <div className="flex items-start space-x-3">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                  status !== 'idle' ? 'bg-green-500 text-white' : 'bg-gray-300 text-gray-600'
                }`}>
                  1
                </div>
                <div>
                  <p className="font-medium text-gray-800">{t('liveness.guide.step1Title')}</p>
                  <p className="text-sm text-gray-600">{t('liveness.guide.step1Desc')}</p>
                </div>
              </div>

              <div className="flex items-start space-x-3">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                  passedCount >= 1 ? 'bg-green-500 text-white' :
                  status === 'challenging' ? 'bg-blue-500 text-white animate-pulse' :
                  'bg-gray-300 text-gray-600'
                }`}>
                  2
                </div>
                <div>
                  <p className="font-medium text-gray-800">{t('liveness.guide.step2Title')}</p>
                  <p className="text-sm text-gray-600">{t('liveness.guide.step2Desc')}</p>
                </div>
              </div>

              <div className="flex items-start space-x-3">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                  passedCount >= 2 ? 'bg-green-500 text-white' :
                  passedCount === 1 && status === 'challenging' ? 'bg-blue-500 text-white animate-pulse' :
                  'bg-gray-300 text-gray-600'
                }`}>
                  3
                </div>
                <div>
                  <p className="font-medium text-gray-800">{t('liveness.guide.step3Title')}</p>
                  <p className="text-sm text-gray-600">{t('liveness.guide.step3Desc')}</p>
                </div>
              </div>

              <div className="flex items-start space-x-3">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                  status === 'passed' ? 'bg-green-500 text-white' : 'bg-gray-300 text-gray-600'
                }`}>
                  4
                </div>
                <div>
                  <p className="font-medium text-gray-800">{t('liveness.guide.step4Title')}</p>
                  <p className="text-sm text-gray-600">{t('liveness.guide.step4Desc')}</p>
                </div>
              </div>
            </div>
          </div>

          {/* 인식 정보 */}
          {faceName && (
            <div className="bg-white rounded-lg shadow-md p-4 sm:p-6">
              <h3 className="text-lg font-semibold text-gray-800 mb-3">
                {t('liveness.recognized.title')}
              </h3>
              <div className="flex items-center space-x-3">
                <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
                  <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                      d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                </div>
                <div>
                  <p className="font-medium text-gray-800">{faceName}</p>
                  {faceConfidence && (
                    <p className="text-sm text-gray-600">
                      {t('liveness.recognized.confidence')}: {Math.round(faceConfidence * 100)}%
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* 안내사항 */}
          <div className="bg-blue-50 rounded-lg p-4">
            <div className="flex items-start space-x-2">
              <svg className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div>
                <p className="text-sm font-medium text-blue-800">{t('liveness.info.title')}</p>
                <ul className="text-sm text-blue-700 mt-1 space-y-1">
                  <li>{t('liveness.info.tip1')}</li>
                  <li>{t('liveness.info.tip2')}</li>
                  <li>{t('liveness.info.tip3')}</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default LivenessCheck;
