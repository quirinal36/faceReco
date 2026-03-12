import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import FaceRegistration from './pages/FaceRegistration';
import FaceList from './pages/FaceList';
import Attendance from './pages/Attendance';
import LivenessCheck from './pages/LivenessCheck';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="register" element={<FaceRegistration />} />
          <Route path="faces" element={<FaceList />} />
          <Route path="attendance" element={<Attendance />} />
          <Route path="liveness" element={<LivenessCheck />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;
