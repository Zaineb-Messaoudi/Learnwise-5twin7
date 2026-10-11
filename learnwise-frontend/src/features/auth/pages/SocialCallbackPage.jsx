import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import './SocialCallbackPage.css';

export function SocialCallbackPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { socialLogin } = useAuth();
  const [status, setStatus] = useState('loading');
  const [error, setError] = useState('');

  useEffect(() => {
    const handleCallback = async () => {
      const params = new URLSearchParams(window.location.search);
      const code = params.get('code');
      const stateStr = params.get('state');
      const oauthError = params.get('error');

      if (oauthError) {
        setStatus('error');
        setError(`Social login failed: ${params.get('error_description') || oauthError}`);
        return;
      }

      if (!code || !stateStr) {
        setStatus('error');
        setError('Invalid callback. Missing authorization code or state.');
        return;
      }

      let state;
      try {
        state = JSON.parse(stateStr);
      } catch {
        setStatus('error');
        setError('Invalid state parameter.');
        return;
      }

      const { provider, role, next } = state;

      try {
        const result = await socialLogin(provider, null, role, code);
        if (result.success) {
          setStatus('success');
          setTimeout(() => navigate(next || '/student/dashboard', { replace: true }), 1500);
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