import { useEffect, useRef, useState } from 'react';
import { clearAuth, getStoredToken } from '../auth/session';
import { getApiUrl } from '../services/api';

const MAX_PENDING_BYTES = 5 * 1024 * 1024;

function appendBytes(left, right) {
  const combined = new Uint8Array(left.length + right.length);
  combined.set(left);
  combined.set(right, left.length);
  return combined;
}

function findMarker(bytes, first, second, fromIndex = 0) {
  for (let index = fromIndex; index < bytes.length - 1; index += 1) {
    if (bytes[index] === first && bytes[index + 1] === second) return index;
  }
  return -1;
}

function AuthenticatedMjpeg({ alt, className, onError, onFrame }) {
  const [frameUrl, setFrameUrl] = useState(null);
  const currentUrlRef = useRef(null);
  const onErrorRef = useRef(onError);
  const onFrameRef = useRef(onFrame);

  onErrorRef.current = onError;
  onFrameRef.current = onFrame;

  useEffect(() => {
    const controller = new AbortController();
    let reader = null;
    let pending = new Uint8Array(0);
    let receivedFrame = false;

    const publishFrame = (bytes) => {
      const nextUrl = URL.createObjectURL(new Blob([bytes], { type: 'image/jpeg' }));
      const previousUrl = currentUrlRef.current;
      currentUrlRef.current = nextUrl;
      setFrameUrl(nextUrl);
      if (previousUrl) URL.revokeObjectURL(previousUrl);

      if (!receivedFrame) {
        receivedFrame = true;
        onFrameRef.current?.();
      }
    };

    const consumeFrames = () => {
      while (pending.length > 1) {
        const start = findMarker(pending, 0xff, 0xd8);
        if (start === -1) {
          pending = pending[pending.length - 1] === 0xff
            ? pending.slice(-1)
            : new Uint8Array(0);
          return;
        }

        const end = findMarker(pending, 0xff, 0xd9, start + 2);
        if (end === -1) {
          if (start > 0) pending = pending.slice(start);
          if (pending.length > MAX_PENDING_BYTES) {
            throw new Error('Invalid MJPEG frame');
          }
          return;
        }

        publishFrame(pending.slice(start, end + 2));
        pending = pending.slice(end + 2);
      }
    };

    const openStream = async () => {
      try {
        const token = getStoredToken();
        if (!token) {
          clearAuth();
          return;
        }

        const response = await fetch(getApiUrl('/api/camera/stream'), {
          method: 'GET',
          headers: {
            Accept: 'multipart/x-mixed-replace',
            Authorization: `Bearer ${token}`,
          },
          cache: 'no-store',
          signal: controller.signal,
        });

        if (response.status === 401) {
          clearAuth();
          return;
        }
        if (!response.ok || !response.body) {
          throw new Error('Camera stream unavailable');
        }

        reader = response.body.getReader();
        while (!controller.signal.aborted) {
          const { done, value } = await reader.read();
          if (done) break;
          if (controller.signal.aborted) break;
          pending = appendBytes(pending, value);
          consumeFrames();
        }

        if (!controller.signal.aborted && !receivedFrame) onErrorRef.current?.();
      } catch {
        if (!controller.signal.aborted) onErrorRef.current?.();
      }
    };

    openStream();

    return () => {
      controller.abort();
      if (reader) reader.cancel().catch(() => {});
      if (currentUrlRef.current) {
        URL.revokeObjectURL(currentUrlRef.current);
        currentUrlRef.current = null;
      }
    };
  }, []);

  if (!frameUrl) {
    return <div className={className} aria-label={alt} />;
  }

  return <img src={frameUrl} alt={alt} className={className} />;
}

export default AuthenticatedMjpeg;
