import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Loader2, CheckCircle, AlertCircle, User, Video, Mail, X, Check } from 'lucide-react';
import { useAuth } from '../../../contexts/AuthContext';
import { FaceCapture } from '../components/FaceCapture';
import { authApi } from '../../../api/auth.api';
import { isBackendApiEnabled } from '../../../api/client';
import './CompleteProfilePage.css';

function getRouteRole(backendRole) {
  const map = { etudiant: 'student', professeur: 'teacher', admin: 'admin' };
  return map[backendRole] || 'student';
}

export function CompleteProfilePage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, isAuthenticated, updateUser, getUser, registerFace, getFaceProfile } = useAuth();
  const [status, setStatus] = useState('idle'); // idle | loading | role | face | registering-face | verified | error
  const [error, setError] = useState('');
  const [userData, setUserData] = useState(null);
  const [selectedRole, setSelectedRole] = useState(null);
  const [faceCaptured, setFaceCaptured] = useState(false);
  const [pendingUser, setPendingUser] = useState(null);

  useEffect(() => {
    const incomingUser = location.state?.user;
    const incomingEmail = location.state?.email;

    // If user is already authenticated (tokens in storage), fetch their profile
    // This handles both OAuth users (after social login) and email/password users
    // who just completed email verification
    const initializeProfile = async () => {
      if (incomingUser) {
        // OAuth flow: user data passed in location state
        setUserData(incomingUser);
        setPendingUser(incomingUser);
        if (!incomingUser.role) {
          setStatus('role');
        } else {
          await checkProfileCompletion(incomingUser);
        }
      } else if (incomingEmail && isAuthenticated) {
        // Email/password flow: user comes from email verification, already logged in
        // Fetch full user profile
        setStatus('loading');
        try {
          const response = await getUser();
          if (response.success) {
            const freshUser = response.data;
            setUserData(freshUser);
            setPendingUser(freshUser);
            await checkProfileCompletion(freshUser);
          } else {
            setError('Failed to load user profile.');
            setStatus('error');
          }
        } catch (err) {
          setError('Failed to load user profile.');
          setStatus('error');
        }
      } else if (isAuthenticated) {
        // User is authenticated but no state - fetch profile
        setStatus('loading');
        try {
          const response = await getUser();
          if (response.success) {
            const freshUser = response.data;
            setUserData(freshUser);
            setPendingUser(freshUser);
            await checkProfileCompletion(freshUser);
          } else {
            setError('Failed to load user profile.');
            setStatus('error');
          }
        } catch (err) {
          setError('Failed to load user profile.');
          setStatus('error');
        }
      } else {
        // Not authenticated - redirect to login
        navigate('/auth/login');
      }
    };

    initializeProfile();
  }, [location.state, navigate, isAuthenticated]);

  const checkProfileCompletion = async (user) => {
    if (!isBackendApiEnabled) {
      // Mock mode
      setStatus('verified');
      return;
    }
    try {
      const faceProfile = await getFaceProfile();
      const hasFace = faceProfile.success && faceProfile.data?.is_verified;
      const emailVerified = user.email_verified;

      if (!user.role) {
        setStatus('role');
      } else if (!hasFace) {
        setStatus('face');
      } else if (!emailVerified) {
        setStatus('verifying');
        // Start polling for email verification
        startVerificationPolling();
      } else {
        setStatus('verified');
        // The user is already logged in (tokens were stored at social sign-in); just
        // refresh the stored user object and redirect.
        setTimeout(() => {
          updateUser(user);
          const routeRole = getRouteRole(user.role);
          navigate(`/${routeRole}/dashboard`, { replace: true });
        }, 1000);
      }
    } catch (err) {
      // If face profile doesn't exist (404), treat as "no face"
      if (err.response?.status === 404) {
        setStatus('face');
      } else {
        setError('Failed to check profile completion.');
        setStatus('error');
      }
    }
  };

  const handleRoleSelect = (role) => {
    setSelectedRole(role);
  };

  const confirmRole = async () => {
    if (!selectedRole) {
      setError('Please select a role.');
      return;
    }
    // Map frontend role labels to backend role values (etudiant / professeur).
    const roleMap = { student: 'etudiant', teacher: 'professeur' };
    const backendRole = roleMap[selectedRole] || selectedRole;
    try {
      await authApi.selectRole(backendRole);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to select role.');
      return;
    }
    setStatus('face');
  };

  const handleFaceCapture = async (descriptor, qualityScore, enrollmentImage) => {
    setStatus('registering-face');
    try {
      const response = await registerFace(descriptor, qualityScore, enrollmentImage);
      if (response.success) {
        setFaceCaptured(true);
        // Face registered successfully - email is already verified, redirect to dashboard
        await checkProfileCompletion(pendingUser);
      } else {
        setError(response.error || 'Photo registration failed');
        setStatus('face');
      }
    } catch (err) {
      setError('Photo registration failed. Please try again.');
      setStatus('face');
    }
  };

  // Render functions for each step
  const renderRoleStep = () => (
    <div className="complete-profile-page">
      <div className="complete-profile-card">
        <div className="complete-header">
          <User size={48} />
          <h1>Welcome to Learnwise!</h1>
          <p>Let's finish setting up your account</p>
        </div>

        <div className="role-selection">
          <label className={`role-option ${selectedRole === 'student' ? 'selected' : ''}`} onClick={() => handleRoleSelect('student')}>
            <div className="role-icon student">
              <Video size={24} />
            </div>
            <div className="role-info">
              <strong>Student</strong>
              <span>Learn, practice, and track your progress</span>
            </div>
            <input type="radio" name="role" value="student" checked={selectedRole === 'student'} onChange={() => handleRoleSelect('student')} />
          </label>
          <label className={`role-option ${selectedRole === 'teacher' ? 'selected' : ''}`} onClick={() => handleRoleSelect('teacher')}>
            <div className="role-icon teacher">
              <User size={24} />
            </div>
            <div className="role-info">
              <strong>Educator</strong>
              <span>Create courses, manage students, analyze progress</span>
            </div>
            <input type="radio" name="role" value="teacher" checked={selectedRole === 'teacher'} onChange={() => handleRoleSelect('teacher')} />
          </label>
        </div>

        {error && <div className="error-message">{error}</div>}

        <button className="btn-next" onClick={confirmRole} disabled={!selectedRole}>
          Continue to Add a photo <span>→</span>
        </button>
      </div>
    </div>
  );

  const renderFaceStep = () => (
    <div className="complete-profile-page">
      <div className="complete-profile-card">
        <div className="complete-header">
          <Video size={48} />
          <h1>Add a photo</h1>
          <p>Add a photo of your face using the camera or upload an image</p>
        </div>
        <FaceCapture
          onCapture={handleFaceCapture}
          onError={(err) => setError('Photo capture failed. Please try again.')}
          required={true}
          mode="both"
          defaultMode="camera"
        />
        {error && <div className="error-message">{error}</div>}
      </div>
    </div>
  );

  const renderVerifyingStep = () => (
    <div className="complete-profile-page">
      <div className="complete-profile-card">
        <div className="complete-header">
          <Mail size={48} className="pulse" />
          <h1>Verify your email</h1>
          <p>We've sent a verification link to your email.</p>
          <p className="hint">Click the link to complete your registration</p>
        </div>
        <div className="resend-section">
          <button onClick={resendVerification} disabled={resendCountdown > 0} className="btn-resend">
            {resendCountdown > 0 ? `Resend in {resendCountdown}s` : 'Resend verification email'}
          </button>
        </div>
      </div>
    </div>
  );

  const renderErrorStep = () => (
    <div className="complete-profile-page">
      <div className="complete-profile-card error">
        <AlertCircle size={48} />
        <h1>Something went wrong</h1>
        <p>{error || 'An unexpected error occurred'}</p>
        <button onClick={() => setStatus('role')} className="btn-retry">
          Try Again
        </button>
      </div>
    </div>
  );

  const renderLoadingStep = () => (
    <div className="complete-profile-page">
      <div className="complete-profile-card">
        <div className="callback-icon loading">
          <Loader2 className="spin" size={32} />
        </div>
        <h1>Checking your profile…</h1>
        <p>Please wait while we check what needs to be completed.</p>
      </div>
    </div>
  );

  const renderVerifiedStep = () => (
    <div className="complete-profile-page">
      <div className="complete-profile-card verified">
        <div className="verified-icon"><CheckCircle size={64} /></div>
        <h1>All Set!</h1>
        <p>Your profile is complete. Redirecting to dashboard…</p>
        <div className="verified-loader"><Loader2 size={24} className="spin" /></div>
      </div>
    </div>
  );

  // Render based on status
  switch (status) {
    case 'idle':
    case 'loading':
      return renderLoadingStep();
    case 'error':
      return renderErrorStep();
    case 'role':
      return renderRoleStep();
    case 'face':
    case 'registering-face':
      return renderFaceStep();
    case 'verifying':
      return renderVerifyingStep();
    case 'verified':
      return renderVerifiedStep();
    default:
      return renderLoadingStep();
  }
}

export default CompleteProfilePage;