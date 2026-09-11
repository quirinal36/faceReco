import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import numpy as np
from api import routes


def test_live_frames_do_not_wait_or_queue_inference():
    entered = threading.Event()
    finish = threading.Event()
    calls = []
    class Recognizer:
        def detect_and_extract(self, frame):
            calls.append(frame)
            entered.set()
            assert finish.wait(5)
            return []
    class Camera:
        def read_frame(self):
            return True, np.zeros((48, 64, 3), dtype=np.uint8)
    stream = routes.generate_frames(Recognizer(), None, Camera())
    try:
        assert next(stream).startswith(b'--frame')
        assert entered.wait(1)
        with ThreadPoolExecutor(max_workers=1) as consumer:
            frames = consumer.submit(lambda: [next(stream) for _ in range(30)])
            assert len(frames.result(timeout=2)) == 30
        assert len(calls) == 1
    finally:
        stream.close()
        finish.set()


def test_matching_and_attendance_happen_once_per_analysis():
    class Recognizer:
        def detect_and_extract(self, frame):
            return [{'bbox': [0, 0, 20, 20], 'embedding': np.ones(512), 'age': 30, 'gender': 1}]
    class Database:
        faces = {'person': {'metadata': {'name': 'Test'}}}
        def recognize_face(self, embedding):
            return 'person', 0.9
    with patch.object(routes, '_record_attendance_if_needed') as record:
        overlays, faces, count = routes._analyze_camera_frame(Recognizer(), Database(), None)
        assert count == 1 and faces[0]['name'] == 'Test'
        assert len(overlays) == 1
        record.assert_called_once_with('person', 'Test', 0.9)
