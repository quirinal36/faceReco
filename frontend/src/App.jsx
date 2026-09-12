import { BrowserRouter as Router, Navigate, Route, Routes } from 'react-router-dom';
import { AUTH_ROLES } from './auth/session';
import useAuth from './auth/useAuth';
import AuthGate from './components/AuthGate';
import Layout from './components/Layout';
import Attendance from './pages/Attendance';
import Dashboard from './pages/Dashboard';
import FaceList from './pages/FaceList';
import FaceRegistration from './pages/FaceRegistration';
import LivenessCheck from './pages/LivenessCheck';

function RoleRoutes() {
  const { role } = useAuth();
  const homePath = role === AUTH_ROLES.DEVICE ? '/liveness' : '/';

  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        {role === AUTH_ROLES.OPERATOR && (
          <>
            <Route index element={<Dashboard />} />
            <Route path="register" element={<FaceRegistration />} />
            <Route path="faces" element={<FaceList />} />
            <Route path="attendance" element={<Attendance />} />
          </>
        )}
        {role === AUTH_ROLES.DEVICE && (
          <>
            <Route index element={<Navigate to="/liveness" replace />} />
            <Route path="liveness" element={<LivenessCheck />} />
          </>
        )}
        <Route path="*" element={<Navigate to={homePath} replace />} />
      </Route>
    </Routes>
  );
}

function App() {
  return (
    <AuthGate>
      <Router>
        <RoleRoutes />
      </Router>
    </AuthGate>
  );
}

export default App;
