import { useEffect, useState } from 'react';
import { faceAPI } from '../services/api';

function ProtectedThumbnail({ alt, className, faceId, fallback }) {
  const [objectUrl, setObjectUrl] = useState(null);

  useEffect(() => {
    const controller = new AbortController();
    let createdUrl = null;

    const loadThumbnail = async () => {
      try {
        const response = await faceAPI.getFaceThumbnail(faceId, controller.signal);
        if (controller.signal.aborted) return;

        createdUrl = URL.createObjectURL(response.data);
        setObjectUrl(createdUrl);
      } catch {
        if (!controller.signal.aborted) {
          setObjectUrl(null);
        }
      }
    };

    loadThumbnail();

    return () => {
      controller.abort();
      if (createdUrl) URL.revokeObjectURL(createdUrl);
    };
  }, [faceId]);

  if (!objectUrl) return fallback;

  return <img src={objectUrl} alt={alt} className={className} />;
}

export default ProtectedThumbnail;
