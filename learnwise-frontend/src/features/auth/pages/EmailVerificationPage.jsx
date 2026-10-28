import React, { useEffect, useRef, useState } from 'react';
import { Link, useLocation, useSearchParams } from 'react-router-dom';
import { Mail, Loader2, CheckCircle, AlertCircle, RotateCcw } from 'lucide-react';
import { useAuth } from '../../../contexts/AuthContext';
import { authApi } from '../../../api/auth.api';
import { BrandMark } from '../../public/components/BrandMark';
import './EmailVerificationPage.css';

const DIGIT_COUNT = 6;

export function EmailVerificationPage() {
  const [searchParams] = useSearchParams();
  const location = useLocation();
  const { verifyEmail } = useAuth();
  const token = searchParams.get('token');
  const email = location.state?.email || searchParams.get('email') || '';

  const [status, setStatus] = useState(token ? 'verifying' : 'pending');
  const [error, setError] = useState('');
  const [resendLoading, setResendLoading] = useState(false);
  const [code, setCode] = useState(Array(DIGIT_COUNT).fill(''));
  const [codeLoading, setCodeLoading] = useState(false);
  const [codeError, setCodeError] = useState('');
  const inputs = useRef([]);

  const codeString = code.join('');

  useEffect(() => {
    if (!token) return;
    verifyEmail(token).then(result => {
      setStatus(result.success ? 'success' : 'error');
      if (!result.success) setError(result.error || '');
    });
  }, [token, verifyEmail]);

  const moveFocus = (index, value) => {
    if (value && index < DIGIT_COUNT - 1) {
      inputs.current[index + 1]?.focus();
    } else if (!value && index > 0) {
      inputs.current[index - 1]?.focus();
    }
  };

  const handleDigitChange = (e, index) => {
    const { value } = e.target;
    if (/^\d$/.test(value) || value === '') {
      const next = code.slice();
      next[index] = value;
      setCode(next);
      setCodeError('');
      moveFocus(index, value);
    }
  };

  const handlePaste = e => {
    e.preventDefault();
    const pasted = (e.clipboardData || window.clipboardData)
      .getData('text')
      .replace(/\D/g, '')
      .slice(0, DIGIT_COUNT);
    const next = pasted.split('').concat(code.slice(pasted.length));
    setCode(next.slice(0, DIGIT_COUNT));
    if (pasted.length === DIGIT_COUNT) handleVerifyCode();
  };

  const handleKeyDown = (e, index) => {
    if (e.key === 'Backspace' && !e.target.value && index > 0) {
      inputs.current[index - 1]?.focus();
    }
  };

  const handleVerifyCode = async () => {
    if (codeString.length !== DIGIT_COUNT) return;
    setCodeLoading(true);
    setCodeError('');
    try {
      await authApi.verifyCode(codeString, email);
      setStatus('success');
    } catch (cause) {
      setCodeError(cause?.response?.data?.detail || 'Invalid verification code.');
      setStatus('error');
    } finally {
      setCodeLoading(false);
    }
  };

  const handleResend = async () => {
    setResendLoading(true);
    setError('');
    try {
      await authApi.resendVerificationPublic(email);
      setStatus('resent');
    } catch (cause) {
      setError(cause?.response?.data?.detail || 'Failed to resend verification email.');
    } finally {
      setResendLoading(false);
    }
  };

  const renderContent = () => {
    switch (status) {
      case 'pending':
        return (
          <div className="verification-state pending">
            <BrandMark className="verification-logo" />
            <div className="verification-heading">
              <span className="verification-kicker">Verify your email</span>
              <h1>Check your inbox</h1>
              <p>
                {email ? (
                  <>We sent a verification link to <strong>{email}</strong>. Or enter the 6-digit code below.</>
                ) : (
                  'We sent a verification link to your email address. Or enter the 6-digit code below.'
                )}
              </p>
            </div>
            {error && <p className="form-error" role="alert">{error}</p>}
            <div className="otp-group">
              <label className="otp-label">Verification code</label>
              <div className="otp-inputs">
                {code.map((digit, i) => (
                  <input
                    key={i}
                    ref={el => (inputs.current[i] = el)}
                    type="text"
                    inputMode="numeric"
                    pattern="[0-9]*"
                    maxLength={1}
                    value={digit}
                    onChange={e => handleDigitChange(e, i)}
                    onPaste={handlePaste}
                    onKeyDown={e => handleKeyDown(e, i)}
                    className={`otp-box ${digit ? 'filled' : ''} ${codeError ? 'error' : ''}`}
                    autoComplete="one-time-code"
                  />
                ))}
              </div>
              <div className="otp-hint">
                Didn&rsquo;t receive it? <a onClick={handleResend}>Resend code</a>
              </div>
            </div>
            <div className="verification-actions">
              <button
                onClick={handleVerifyCode}
                disabled={codeLoading || codeString.length !== DIGIT_COUNT}
                className="button button-primary"
              >
                {codeLoading ? <Loader2 size={16} /> : 'Verify code'}
              </button>
              <button onClick={handleResend} disabled={resendLoading || !email} className="button button-secondary">
                {resendLoading ? <Loader2 size={16} /> : <><RotateCcw size={16} /> Resend verification email</>}
              </button>
              <Link to="/auth/login" className="text-link">Back to login</Link>
            </div>
          </div>
        );
      case 'verifying':
        return (
          <div className="verification-state verifying">
            <BrandMark className="verification-logo" />
            <div className="verification-heading">
              <span className="verification-kicker">Verifying</span>
              <h1>Verifying your email...</h1>
              <p>Please wait while we confirm your email address.</p>
            </div>
            <div className="verification-actions center">
              <Loader2 className="loader-inline" size={20} />
            </div>
          </div>
        );
      case 'success':
        return (
          <div className="verification-state success">
            <BrandMark className="verification-logo" />
            <div className="verification-heading">
              <span className="verification-kicker verification-kicker-success">Verified</span>
              <h1>Email verified!</h1>
              <p>Your email address has been confirmed. Completing your profile…</p>
            </div>
            <Link to="/auth/complete-profile" className="button button-primary" state={{ email }}>
              Continue to profile setup <span style={{ marginLeft: 6 }}>&rarr;</span>
            </Link>
          </div>
        );
      case 'error':
        return (
          <div className="verification-state error">
            <BrandMark className="verification-logo" />
            <div className="verification-heading">
              <span className="verification-kicker verification-kicker-error">Verification failed</span>
              <h1>Invalid code</h1>
              <p>{error || codeError || 'The verification link or code is invalid or has expired.'}</p>
            </div>
            <div className="verification-actions">
              <button onClick={handleResend} disabled={resendLoading || !email} className="button button-secondary">
                {resendLoading ? <Loader2 size={16} /> : <><RotateCcw size={16} /> Resend verification email</>}
              </button>
              <Link to="/auth/register" className="text-link">Create new account</Link>
            </div>
          </div>
        );
      case 'resent':
        return (
          <div className="verification-state resent">
            <BrandMark className="verification-logo" />
            <div className="verification-heading">
              <span className="verification-kicker">Verification email sent</span>
              <h1>Verification email sent!</h1>
              <p>A new verification link has been sent to your email. Please check your inbox.</p>
            </div>
            <button onClick={() => setStatus('pending')} className="button button-secondary">Back</button>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <main className="verification-page">
      <div className="verification-card">
        {renderContent()}
      </div>
    </main>
  );
}
