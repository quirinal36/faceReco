import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import useAuth from '../auth/useAuth';
import LanguageSwitcher from './LanguageSwitcher';

function AuthGate({ children }) {
  const { t } = useTranslation();
  const { authenticate, isAuthenticated, isChecking } = useAuth();
  const [credential, setCredential] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setIsSubmitting(true);

    const result = await authenticate(credential);
    if (!result.ok) {
      setError(t(`auth.errors.${result.reason}`));
      setCredential('');
    }

    setIsSubmitting(false);
  };

  if (isChecking) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
        <div className="text-gray-600">{t('app.loading')}</div>
      </div>
    );
  }

  if (isAuthenticated) {
    return children;
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
      <div className="absolute right-4 top-4">
        <LanguageSwitcher />
      </div>
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-md rounded-xl bg-white p-6 sm:p-8 shadow-lg"
      >
        <div className="mb-6">
          <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-blue-600 text-white">
            <svg className="h-7 w-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 11c0-1.657 1.343-3 3-3s3 1.343 3 3v2m-8 8h10a2 2 0 002-2v-6a2 2 0 00-2-2H10a2 2 0 00-2 2v6a2 2 0 002 2zm2-10V7a5 5 0 00-10 0v4" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-gray-900">{t('auth.title')}</h1>
          <p className="mt-2 text-sm text-gray-600">{t('auth.description')}</p>
        </div>

        <label htmlFor="runtime-credential" className="block text-sm font-medium text-gray-700">
          {t('auth.credential')}
        </label>
        <input
          id="runtime-credential"
          name="credential"
          type="password"
          autoComplete="off"
          autoCapitalize="none"
          spellCheck="false"
          value={credential}
          onChange={(event) => setCredential(event.target.value)}
          className="mt-2 w-full rounded-lg border border-gray-300 px-3 py-3 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
          disabled={isSubmitting}
          required
          autoFocus
        />

        {error && (
          <p role="alert" className="mt-3 rounded-lg bg-red-50 p-3 text-sm text-red-700">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={isSubmitting || !credential.trim()}
          className="mt-5 w-full rounded-lg bg-blue-600 px-4 py-3 font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-gray-300"
        >
          {isSubmitting ? t('auth.validating') : t('auth.signIn')}
        </button>
        <p className="mt-4 text-xs text-gray-500">{t('auth.sessionNotice')}</p>
      </form>
    </div>
  );
}

export default AuthGate;
