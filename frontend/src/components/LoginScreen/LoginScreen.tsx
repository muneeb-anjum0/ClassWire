import React, { useEffect, useState } from 'react';
import { AlertCircle, Loader } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { BACKEND_WAKE_EVENT } from '../../services/api';
import './LoginScreen.css';

const LEGAL_ACCEPTANCE_KEY = 'classwire-legal-accepted';

const LoginScreen: React.FC = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [wakeMessage, setWakeMessage] = useState('');
  const [hasAcceptedPrivacy, setHasAcceptedPrivacy] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.localStorage.getItem(LEGAL_ACCEPTANCE_KEY) === 'true';
  });
  const [hasAcceptedTerms, setHasAcceptedTerms] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.localStorage.getItem(LEGAL_ACCEPTANCE_KEY) === 'true';
  });

  const { loginWithGmail, authenticationError } = useAuth();
  const hasAcceptedLegal = hasAcceptedPrivacy && hasAcceptedTerms;

  useEffect(() => {
    const handleBackendWakeState = (event: Event) => {
      const { active, message } = (event as CustomEvent<{ active: boolean; message?: string }>).detail;
      setWakeMessage(active ? message || 'Backend is waking up. The first request can take a moment.' : '');
    };

    window.addEventListener(BACKEND_WAKE_EVENT, handleBackendWakeState);
    return () => window.removeEventListener(BACKEND_WAKE_EVENT, handleBackendWakeState);
  }, []);

  const handleGmailLogin = async () => {
    if (isLoading) return;

    if (!hasAcceptedLegal) {
      setError('Please accept the Privacy Policy and Terms of Service to continue.');
      return;
    }

    setIsLoading(true);
    setError('');
    window.localStorage.setItem(LEGAL_ACCEPTANCE_KEY, 'true');

    try {
      const success = await loginWithGmail();

      if (!success) {
        setError('Gmail authentication failed. Please try again.');
        setIsLoading(false);
      }
    } catch (authError) {
      console.error('[LoginScreen] Gmail login error:', authError);
      const message = authError instanceof Error ? authError.message : 'An error occurred during Gmail authentication. Please try again.';
      setError(message);
      setIsLoading(false);
    }
  };

  return (
    <main className="login-page">
      <section className="login-card">
        <div className="login-card__header">
          <h1>ClassWire: SZABIST timetable search</h1>
          <p className="login-copy">
            Search SZABIST Islamabad class schedules, courses, sections, and faculty availability from your timetable emails.
          </p>
        </div>

        <button
          type="button"
          className="gmail-btn"
          onClick={handleGmailLogin}
          disabled={isLoading || !hasAcceptedLegal}
          aria-busy={isLoading}
        >
          <span className="gmail-icon-wrap">
            {isLoading ? (
              <span className="spinner" aria-hidden="true" />
            ) : (
              <img src="/gmail.svg" alt="" className="gmail-mark" />
            )}
          </span>
          <span>{wakeMessage ? 'Waking backend...' : isLoading ? 'Connecting...' : 'Continue with Google'}</span>
        </button>

        <div className="legal-consent" role="group" aria-label="Privacy and terms agreement">
          <label className="legal-consent__check">
            <input
              type="checkbox"
              checked={hasAcceptedPrivacy}
              onChange={(event) => setHasAcceptedPrivacy(event.target.checked)}
            />
            <span>
              I agree to the <a href="/privacy">Privacy Policy</a>.
            </span>
          </label>

          <label className="legal-consent__check">
            <input
              type="checkbox"
              checked={hasAcceptedTerms}
              onChange={(event) => setHasAcceptedTerms(event.target.checked)}
            />
            <span>
              I agree to the <a href="/terms">Terms of Service</a>.
            </span>
          </label>
        </div>

        {wakeMessage && (
          <div className="status-box status-box--info" role="status">
            <Loader className="status-icon status-icon--spin" />
            <div>
              <p className="status-title">Starting backend</p>
              <p className="status-copy">{wakeMessage}</p>
            </div>
          </div>
        )}

        {(error || authenticationError) && (
          <div className="status-box status-box--error" role="alert">
            <AlertCircle className="status-icon" />
            <div>
              <p className="status-title">
                {(error || authenticationError).includes('Unable to reach the backend')
                    ? 'Backend unavailable'
                    : 'Authentication failed'}
              </p>
              <p className="status-copy">
                {(error || authenticationError).includes('Request failed with status code 500')
                    ? 'The backend could not start the Google OAuth flow. Restart the Flask server once, then try again.'
                    : error || authenticationError}
              </p>
            </div>
          </div>
        )}

        <footer className="login-footer">
          <span>Read-only Gmail access for timetable parsing.</span>
          <span className="login-footer__disclaimer">Independent student utility, not an official SZABIST service.</span>
          <div className="legal-links">
            <a href="/privacy">Privacy</a>
            <span aria-hidden="true">/</span>
            <a href="/terms">Terms</a>
          </div>
        </footer>
      </section>
    </main>
  );
};

export default LoginScreen;
