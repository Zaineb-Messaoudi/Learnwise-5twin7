import React, { useState, useEffect } from 'react';
import { Loader2, AlertCircle, Mail } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import { authApi } from '../../../api/auth.api';
import { useAuth } from '../../../contexts/AuthContext';
import { FaceCapture } from '../components/FaceCapture';
import { Logo } from '../../../layouts/AppShell';
import './FaceCapturePage.css';

function getRouteRole(backendRole) {
  const map = { etudiant: 'student', professeur: 'teacher', admin: 'admin' };
  return map[backendRole] || 'student';
}

export function FaceCapturePage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { registerFace, login } = useAuth();
  const [status, setStatus] = useState('idle'); // idle | capturing | registering | verifying | verified | error
  const [error, setError] = useState('');
  const [email, setEmail] = useState('');
  const [resendCountdown, setResendCountdown] = useState(0);

  const pendingUser = searchParams.get('user');

  useEffect(() => {
    if (!pendingUser) {
      navigate('/auth/register');
      return;
    }
    try {
      const userData = JSON.parse(decodeURIComponent(pendingUser));
      setEmail(userData.email);
    } catch {
      navigate('/auth/register');
    }
  }, [pendingUser, navigate]);

  const handleFaceCapture = async (descriptor, qualityScore, enrollmentImage) => {
    setStatus('registering');
    setError('');
    try {
      const response = await registerFace(descriptor, qualityScore, enrollmentImage);
      if (response.success) {
        setStatus('verifying');
      } else {
        setError(response.error || 'Photo registration failed. Please try again.');
        setStatus('error');
      }
    } catch (err) {
      setError(err.message || 'Photo registration failed. Please try again.');
      setStatus('error');
    }
  };

  const resendVerification = async () => {
    if (resendCountdown > 0) return;
    setError('');
    try {
      await authApi.resendVerification();
      setResendCountdown(60);
      const countdown = setInterval(() => {
        setResendCountdown(prev => {
          if (prev <= 1) {
            clearInterval(countdown);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    } catch (err) {
      setError('Failed to resend verification email.');
    }
  };

  if (status === 'verified') {
    return (
      <main className="face-capture-page">
        <div className="face-capture-container">
          <div className="face-capture-card verified">
            <div className="verified-icon"><CheckCircle size={64} /></div>
            <h1>Photo registered successfully!</h1>
            <p>Your face has been enrolled. We've sent a verification email to <strong>{email}</strong>.</p>
            <p className="verifying-hint">Click the link in the email, then continue to log in.</p>
            <button onClick={handleVerifiedContinue} className="btn-primary">
              Go to Dashboard
            </button>
            <p className="verifying-hint">Or <a href="/auth/login">sign in manually</a></p>
          </div>
        </div>
      </main>
    );
  }

  if (status === 'idle') {
    setStatus('capturing');
  }

  return (
    <main className="face-capture-page">
      <div className="face-capture-container">
        <div className="face-capture-card">
          <div className="face-capture-header">
            <Logo />
            <h1>Add a photo</h1>
            <p>Add a photo of your face using the camera or upload an image</p>
          </div>

          {status === 'capturing' && (
            <FaceCapture
              onCapture={handleFaceCapture}
              onError={(err) => setError('Photo capture failed. Please try again.')}
              required={true}
              mode="both"
              defaultMode="camera"
            />
          )}

          {status === 'registering' && (
            <div className="face-processing">
              <Loader2 size={48} className="spin" />
              <h3>Registering your photo…</h3>
              <p>This takes a few seconds</p>
            </div>
          )}

          {status === 'verifying' && (
            <div className="face-verifying">
              <Mail size={48} className="pulse" />
              <h3>Check your email</h3>
              <p>We sent a verification link to <strong>{email}</strong></p>
              <p className="verifying-hint">Click the link in the email to verify your account</p>
              <div className="resend-section">
                {resendCountdown > 0 ? (
                  <span className="countdown">Resend available in {resendCountdown}s</span>
                ) : (
                  <button onClick={resendVerification} className="btn-resend">
                    Didn't receive it? Resend email
                  </button>
                )}
              </div>
            </div>
          )}

          {status === 'error' && (
            <div className="face-error">
              <AlertCircle size={48} />
              <h3>Something went wrong</h3>
              <p>{error || 'An unexpected error occurred'}</p>
              <button onClick={() => setStatus('capturing')} className="btn-retry">
                Try Again
              </button>
            </div>
          )}
        </div>
      </div>
    </main>
    );
  };

export default FaceCapturePage;