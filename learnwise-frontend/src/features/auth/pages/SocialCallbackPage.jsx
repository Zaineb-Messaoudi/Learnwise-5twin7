import React, { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import { authApi } from '../../api/auth.api';
import { useAuth } from '../../contexts/AuthContext';
import './SocialCallbackPage.css';

export function SocialCallbackPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { socialLogin, login } = useAuth();
  const [status, setStatus] = useState('loading');
  const [error, setError] = useState('');

  useEffect(() => {
    const handleCallback = async () => {
      const hash = window.location.hash.substring(1);
      const params = new URLSearchParams(hash);
      const accessToken = params.get('access_token');
      const provider = searchParams.get('provider') || params.get('provider');
      const role = searchParams.get('role') || 'etudiant';
      const next = searchParams.get('next') || '/student/dashboard';

      if (!accessToken || !provider) {
        setStatus('error');
        setError('Invalid callback. Missing access token or provider.');
        return;
      }

      try {
        const result = await socialLogin(provider, accessToken, role);
        if (result.success) {
          setStatus('success');
          setTimeout(() => navigate(next, { replace: true }), 1500);
        } else {
          setStatus('error');
          setError(result.error);
        }
      } catch (err) {
        setStatus('error');
        setError('Social login failed. Please try again.');
      }
    };

    handleCallback();
  }, [searchParams, socialLogin, navigate]);

  if (status === 'loading') {
    return (
      <div className="callback-page">
        <div className="callback-card">
          <div className="callback-icon loading">
            <Loader2 className="spin" size={32} />
          </div>
          <h1>Completing sign in...</h1>
          <p>Please wait while we connect your account.</p>
        </div>
      </div>
    );
  }

  if (status === 'success') {
    return (
      <div className="callback-page">
        <div className="callback-card">
          <div className="callback-icon success">
            <CheckCircle size={48} />
          </div>
          <h1>Welcome back!</h1>
          <p>You've been signed in successfully. Redirecting...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="callback-page">
      <div className="callback-card">
        <div className="callback-icon error">
          <AlertCircle size={48} />
        </div>
        <h1>Sign in failed</h1>
        <p>{error || 'An error occurred during social sign in.'}</p>
        <a href="/auth/login" className="button primary">Try again</a>
      </div>
    </div>
  );
}