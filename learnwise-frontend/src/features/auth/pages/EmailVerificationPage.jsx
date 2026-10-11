import React, { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Mail, Loader2, CheckCircle, AlertCircle, RotateCcw } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { PublicFrame } from '../components/PublicFrame';
import './EmailVerificationPage.css';

export function EmailVerificationPage() {
  const [searchParams] = useSearchParams();
  const { verifyEmail, resendVerification, loading, error, clearError } = useAuth();
  const [status, setStatus] = useState('verifying');
  const [resendLoading, setResendLoading] = useState(false);

  const token = searchParams.get('token');

  useEffect(() => {
    if (token) {
      verifyEmail(token).then(result => {
        if (result.success) {
          setStatus('success');
        } else {
          setStatus('error');
        }
      });
    } else {
      setStatus('error');
    }
  }, [token, verifyEmail]);

  const handleResend = async () => {
    setResendLoading(true);
    clearError();
    const result = await resendVerification();
    setResendLoading(false);
    if (result.success) {
      setStatus('resent');
    }
  };

  const renderContent = () => {
    switch (status) {
      case 'verifying':
        return (
          <div className="verification-state verifying">
            <div className="verification-icon">
              <Loader2 className="spin" size={32} />
            </div>
            <h1>Verifying your email...</h1>
            <p>Please wait while we confirm your email address.</p>
          </div>
        );
      case 'success':
        return (
          <div className="verification-state success">
            <div className="verification-icon">
              <CheckCircle size={48} />
            </div>
            <h1>Email verified!</h1>
            <p>Your email address has been confirmed. You're now signed in.</p>
            <Link to="/" className="button primary">
              Continue to Learnwise
            </Link>
          </div>
        );
      case 'error':
        return (
          <div className="verification-state error">
            <div className="verification-icon">
              <AlertCircle size={48} />
            </div>
            <h1>Verification failed</h1>
            <p>{error || 'The verification link is invalid or has expired.'}</p>
            <div className="verification-actions">
              <button onClick={handleResend} disabled={resendLoading} className="button secondary">
                {resendLoading ? <Loader2 size={16} /> : <> <RotateCcw size={16} /> Resend verification email</> }
              </button>
              <Link to="/auth/register" className="button primary">
                Create new account
              </Link>
            </div>
          </div>
        );
      case 'resent':
        return (
          <div className="verification-state resent">
            <div className="verification-icon">
              <Mail size={48} />
            </div>
            <h1>Verification email sent!</h1>
            <p>A new verification link has been sent to your email. Please check your inbox.</p>
            <button onClick={() => setStatus('error')} className="button secondary">
              Try another link
            </button>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <PublicFrame>
      <main className="verification-page">
        <div className="verification-card">
          <div className="verification-brand">
            <svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" width="40" height="40">
              <rect width="32" height="32" rx="8" fill="currentColor"/>
              <path d="M8 16L14 22L24 10" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            <span>Learnwise</span>
          </div>
          {renderContent()}
        </div>
      </main>
    </PublicFrame>
  );
}