import React, { useState, useEffect } from 'react';
import { Loader2, AlertCircle, CheckCircle } from 'lucide-react';
import { useSearchParams, useNavigate } from 'react-router-dom';
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
  const { isAuthenticated, updateUser, registerFace, getUser } = useAuth();
  const [status, setStatus] = useState('idle'); // idle | capturing | registering | verified | error
  const [error, setError] = useState('');
  const [email, setEmail] = useState('');

  const [pendingUser, setPendingUser] = useState(null);

  useEffect(() => {
    const incomingUser = searchParams.get('user');

    const initializeProfile = async () => {
      if (incomingUser) {
        // OAuth / registration flow: user data passed in search params
        try {
          const userData = JSON.parse(decodeURIComponent(incomingUser));
          setEmail(userData.email);
          setPendingUser(userData);
          setStatus('capturing');
        } catch {
          navigate('/auth/register');
        }
        return;
      }

      if (isAuthenticated) {
        // Logged-in user completing face verification - fetch their profile
        setStatus('loading');
        try {
          const response = await getUser();
          if (response.success) {
            const freshUser = response.data;
            setEmail(freshUser.email);
            setPendingUser(freshUser);
            setStatus('capturing');
          } else {
            setError('Failed to load user profile.');
            setStatus('error');
          }
        } catch (err) {
          setError('Failed to load user profile.');
          setStatus('error');
        }
        return;
      }

      // Not authenticated and no pending user - redirect to login
      navigate('/auth/login');
    };

    initializeProfile();
  }, [incomingUser, isAuthenticated, navigate, getUser]);

  useEffect(() => {
    if (status === 'idle') {
      setStatus('capturing');
    }
  }, [status]);

  const handleFaceCapture = async (descriptor, qualityScore, enrollmentImage) => {
    setStatus('registering');
    setError('');
    try {
      const response = await registerFace(descriptor, qualityScore, enrollmentImage);
      if (response.success) {
        const pending = pendingUser;
        setStatus('verified');
        setTimeout(() => {
          updateUser({ ...pending, email_verified: pending?.email_verified, two_factor_enabled: pending?.two_factor_enabled });
          const routeRole = getRouteRole(pending?.role || 'etudiant');
          navigate(`/${routeRole}/dashboard`, { replace: true });
        }, 800);
      } else {
        setError(response.error || 'Photo registration failed. Please try again.');
        setStatus('error');
      }
    } catch (err) {
      setError(err.message || 'Photo registration failed. Please try again.');
      setStatus('error');
    }
  };

  const handleVerifiedContinue = () => {
    const routeRole = getRouteRole(pendingUser?.role || 'etudiant');
    navigate(`/${routeRole}/dashboard`, { replace: true });
  };

  if (status === 'verified') {
    return (
      <main className="face-capture-page">
        <div className="face-capture-container">
          <div className="face-capture-card verified">
            <div className="verified-icon"><CheckCircle size={64} /></div>
            <h1>Photo registered successfully!</h1>
            <p>Your face photo has been enrolled. You&apos;re all set.</p>
            <button onClick={handleVerifiedContinue} className="btn-primary">
              Go to Dashboard
            </button>
          </div>
        </div>
      </main>
    );
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
}

export default FaceCapturePage;