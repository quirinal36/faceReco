import { useState, useEffect } from 'react';
import { faceAPI } from '../services/api';

function FaceList() {
  const [faces, setFaces] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [deleteLoading, setDeleteLoading] = useState(null);
  const [addSampleLoading, setAddSampleLoading] = useState(null);
  const [mergeLoading, setMergeLoading] = useState(null);

  useEffect(() => {
    fetchFaces();
  }, []);

  const fetchFaces = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await faceAPI.getFaces();
      setFaces(response.data.faces || []);
    } catch (error) {
      console.error('Failed to fetch faces:', error);
      setError('등록된 얼굴 목록을 불러오는데 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id, name) => {
    if (!window.confirm(`정말로 "${name}"님의 얼굴을 삭제하시겠습니까?`)) {
      return;
    }

    setDeleteLoading(id);

    try {
      await faceAPI.deleteFace(id);
      setFaces(faces.filter((face) => face.face_id !== id));
    } catch (error) {
      console.error('Failed to delete face:', error);
      alert('얼굴 삭제에 실패했습니다.');
    } finally {
      setDeleteLoading(null);
    }
  };

  const handleAddSample = async (faceId, name) => {
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = 'image/*';

    fileInput.onchange = async (e) => {
      const file = e.target.files[0];
      if (!file) return;

      setAddSampleLoading(faceId);

      try {
        const formData = new FormData();
        formData.append('file', file);

        const response = await faceAPI.addFaceSample(faceId, formData);

        if (response.data.success) {
          alert(response.data.message);
          // 목록 새로고침
          fetchFaces();
        } else {
          alert(response.data.message);
        }
      } catch (error) {
        console.error('Failed to add sample:', error);
        alert('샘플 추가에 실패했습니다.');
      } finally {
        setAddSampleLoading(null);
      }
    };

    fileInput.click();
  };

  const handleMerge = async (name) => {
    if (!window.confirm(`정말로 "${name}" 이름을 가진 모든 얼굴을 하나로 통합하시겠습니까?`)) {
      return;
    }

    setMergeLoading(name);

    try {
      const response = await faceAPI.mergeFacesByName(name);

      if (response.data.success) {
        alert(response.data.message);
        // 목록 새로고침
        fetchFaces();
      } else {
        alert(response.data.message);
      }
    } catch (error) {
      console.error('Failed to merge faces:', error);
      alert('얼굴 통합에 실패했습니다.');
    } finally {
      setMergeLoading(null);
    }
  };

  // 중복된 이름 찾기
  const getDuplicateNames = () => {
    const nameCounts = {};
    faces.forEach(face => {
      nameCounts[face.name] = (nameCounts[face.name] || 0) + 1;
    });
    return Object.keys(nameCounts).filter(name => nameCounts[name] > 1);
  };

  const duplicateNames = getDuplicateNames();

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center space-y-4">
          <svg
            className="animate-spin h-12 w-12 text-blue-600 mx-auto"
            fill="none"
            viewBox="0 0 24 24"
          >
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
          <p className="text-gray-600">로딩 중...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-gray-800">등록된 얼굴</h2>
          <p className="text-gray-600 mt-2">
            총 <span className="font-semibold text-blue-600">{faces.length}</span>명의 얼굴이
            등록되어 있습니다
          </p>
          {duplicateNames.length > 0 && (
            <p className="text-orange-600 mt-1 text-sm">
              ⚠️ 중복된 이름: {duplicateNames.join(', ')}
            </p>
          )}
        </div>
        <button
          onClick={fetchFaces}
          className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
          <span>새로고침</span>
        </button>
      </div>

      {error ? (
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
          <svg
            className="w-12 h-12 text-red-400 mx-auto mb-4"
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
          <p className="text-red-800 font-medium">{error}</p>
          <button
            onClick={fetchFaces}
            className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
          >
            다시 시도
          </button>
        </div>
      ) : faces.length === 0 ? (
        <div className="bg-white rounded-lg shadow-md p-12 text-center">
          <svg
            className="w-16 h-16 text-gray-400 mx-auto mb-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
            />
          </svg>
          <h3 className="text-xl font-semibold text-gray-800 mb-2">등록된 얼굴이 없습니다</h3>
          <p className="text-gray-600 mb-6">
            새로운 얼굴을 등록하여 인식 시스템을 시작하세요
          </p>
          <a
            href="/register"
            className="inline-flex items-center space-x-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 6v6m0 0v6m0-6h6m-6 0H6"
              />
            </svg>
            <span>얼굴 등록하기</span>
          </a>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {faces.map((face) => (
            <div
              key={face.face_id}
              className="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow"
            >
              <div className="aspect-square bg-gray-100 relative">
                {face.image_path ? (
                  <img
                    src={`http://localhost:8000${face.image_path}`}
                    alt={face.name}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <svg
                      className="w-24 h-24 text-gray-400"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
                      />
                    </svg>
                  </div>
                )}
              </div>
              <div className="p-4">
                <h3 className="text-lg font-semibold text-gray-800 mb-2">{face.name}</h3>
                <div className="flex items-center justify-between text-sm text-gray-600 mb-2">
                  <span className="text-xs text-gray-500">ID: {face.face_id}</span>
                  {face.registered_at && (
                    <span className="text-xs text-gray-500">
                      {new Date(face.registered_at).toLocaleDateString('ko-KR')}
                    </span>
                  )}
                </div>
                <div className="flex items-center justify-between text-sm mb-3 pb-3 border-b border-gray-100">
                  <div className="flex items-center space-x-1 text-blue-600">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                      />
                    </svg>
                    <span className="font-medium">{face.sample_count || 1}개 샘플</span>
                  </div>
                  <div className="flex items-center space-x-1 text-green-600">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                      />
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                      />
                    </svg>
                    <span className="font-medium">{face.recognition_count || 0}회 인식</span>
                  </div>
                </div>
                <div className="space-y-2">
                  {duplicateNames.includes(face.name) && (
                    <button
                      onClick={() => handleMerge(face.name)}
                      disabled={mergeLoading === face.name}
                      className={`w-full py-2 px-4 rounded-lg transition-colors flex items-center justify-center space-x-2 ${
                        mergeLoading === face.name
                          ? 'bg-gray-300 cursor-not-allowed'
                          : 'bg-orange-50 text-orange-600 hover:bg-orange-100'
                      }`}
                    >
                      {mergeLoading === face.name ? (
                        <>
                          <svg
                            className="animate-spin h-4 w-4"
                            fill="none"
                            viewBox="0 0 24 24"
                          >
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
                          <span>통합 중...</span>
                        </>
                      ) : (
                        <>
                          <svg
                            className="w-4 h-4"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"
                            />
                          </svg>
                          <span>중복 통합</span>
                        </>
                      )}
                    </button>
                  )}
                  <button
                    onClick={() => handleAddSample(face.face_id, face.name)}
                    disabled={addSampleLoading === face.face_id}
                    className={`w-full py-2 px-4 rounded-lg transition-colors flex items-center justify-center space-x-2 ${
                      addSampleLoading === face.face_id
                        ? 'bg-gray-300 cursor-not-allowed'
                        : 'bg-blue-50 text-blue-600 hover:bg-blue-100'
                    }`}
                  >
                    {addSampleLoading === face.face_id ? (
                      <>
                        <svg
                          className="animate-spin h-4 w-4"
                          fill="none"
                          viewBox="0 0 24 24"
                        >
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
                        <span>추가 중...</span>
                      </>
                    ) : (
                      <>
                        <svg
                          className="w-4 h-4"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M12 6v6m0 0v6m0-6h6m-6 0H6"
                          />
                        </svg>
                        <span>샘플 추가</span>
                      </>
                    )}
                  </button>
                  <button
                    onClick={() => handleDelete(face.face_id, face.name)}
                    disabled={deleteLoading === face.face_id}
                    className={`w-full py-2 px-4 rounded-lg transition-colors flex items-center justify-center space-x-2 ${
                      deleteLoading === face.face_id
                        ? 'bg-gray-300 cursor-not-allowed'
                        : 'bg-red-50 text-red-600 hover:bg-red-100'
                    }`}
                  >
                  {deleteLoading === face.face_id ? (
                    <>
                      <svg
                        className="animate-spin h-4 w-4"
                        fill="none"
                        viewBox="0 0 24 24"
                      >
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
                      <span>삭제 중...</span>
                    </>
                  ) : (
                    <>
                      <svg
                        className="w-4 h-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                        />
                      </svg>
                      <span>삭제</span>
                    </>
                  )}
                </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default FaceList;
