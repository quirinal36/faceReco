import { useCallback, useEffect, useMemo, useState } from 'react';
import { authAPI, getHttpStatus } from '../services/api';
import AuthContext from './AuthContext';
import {
  AUTH_CLEARED_EVENT,
  clearAuth,
  getStoredAuth,
  isKnownAuthRole,
  storeAuth,
} from './session';

function AuthProvider({ children }) {
  const [role, setRole] = useState(null);
  const [isChecking, setIsChecking] = useState(true);

  const authenticate = useCallback(async (token) => {
    const candidate = token.trim();
    if (!candidate) {
      return { ok: false, reason: 'invalid' };
    }

    try {
      const response = await authAPI.whoami(candidate);
      const validatedRole = response.data?.role;

      if (!isKnownAuthRole(validatedRole)) {
        return { ok: false, reason: 'invalid' };
      }

      storeAuth(candidate, validatedRole);
      setRole(validatedRole);
      return { ok: true, role: validatedRole };
    } catch (error) {
      const status = getHttpStatus(error);
      return {
        ok: false,
        reason: status === 401 || status === 403 ? 'invalid' : 'unavailable',
      };
    }
  }, []);

  const logout = useCallback(() => {
    clearAuth();
  }, []);

  useEffect(() => {
    let active = true;

    const restoreSession = async () => {
      const stored = getStoredAuth();
      if (!stored) {
        if (active) setIsChecking(false);
        return;
      }

      const result = await authenticate(stored.token);
      if (!active) return;

      if (!result.ok) {
        clearAuth();
      }
      setIsChecking(false);
    };

    const handleAuthCleared = () => {
      setRole(null);
      setIsChecking(false);
    };

    window.addEventListener(AUTH_CLEARED_EVENT, handleAuthCleared);
    restoreSession();

    return () => {
      active = false;
      window.removeEventListener(AUTH_CLEARED_EVENT, handleAuthCleared);
    };
  }, [authenticate]);

  const value = useMemo(() => ({
    authenticate,
    isAuthenticated: Boolean(role),
    isChecking,
    logout,
    role,
  }), [authenticate, isChecking, logout, role]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export default AuthProvider;
