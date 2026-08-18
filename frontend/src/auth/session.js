const AUTH_TOKEN_KEY = 'facereco.auth.token';
const AUTH_ROLE_KEY = 'facereco.auth.role';

export const AUTH_CLEARED_EVENT = 'facereco:auth-cleared';
export const AUTH_ROLES = Object.freeze({
  OPERATOR: 'operator',
  DEVICE: 'device',
});

const isKnownRole = (role) => Object.values(AUTH_ROLES).includes(role);

export function getStoredToken() {
  return sessionStorage.getItem(AUTH_TOKEN_KEY);
}

export function getStoredAuth() {
  const token = getStoredToken();
  const role = sessionStorage.getItem(AUTH_ROLE_KEY);

  if (!token || !isKnownRole(role)) {
    sessionStorage.removeItem(AUTH_TOKEN_KEY);
    sessionStorage.removeItem(AUTH_ROLE_KEY);
    return null;
  }

  return { token, role };
}

export function storeAuth(token, role) {
  if (!token || !isKnownRole(role)) {
    throw new Error('Invalid authentication session');
  }

  sessionStorage.setItem(AUTH_TOKEN_KEY, token);
  sessionStorage.setItem(AUTH_ROLE_KEY, role);
}

export function clearAuth() {
  sessionStorage.removeItem(AUTH_TOKEN_KEY);
  sessionStorage.removeItem(AUTH_ROLE_KEY);
  window.dispatchEvent(new Event(AUTH_CLEARED_EVENT));
}

export function isKnownAuthRole(role) {
  return isKnownRole(role);
}
