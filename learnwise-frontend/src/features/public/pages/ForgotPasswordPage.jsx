import React, { useState } from 'react';
import { ArrowRight, Mail } from 'lucide-react';
import { Link, useLocation, useSearchParams } from 'react-router-dom';
import { authApi } from '../../../api/auth.api';
import { isBackendApiEnabled } from '../../../api/client';
import { PublicFrame } from '../components/PublicFrame';

export function ForgotPasswordPage() {
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const isReset = location.pathname === '/auth/reset-password';
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [complete, setComplete] = useState(false);
  const submit = async event => {
    event.preventDefault();
    setError('');
    if (isReset && password !== confirmation) {
      setError('Passwords do not match.');
      return;
    }
    if (isReset && !searchParams.get('token')) {
      setError('This reset link is missing its token. Request a new link to continue.');
      return;
    }
    setBusy(true);
    try {
      if (isBackendApiEnabled) {
        if (isReset) await authApi.confirmPasswordReset({ token: searchParams.get('token'), password });
        else await authApi.requestPasswordReset(email);
        setComplete(true);
      } else {
        setError('We could not process that request. Please try again later.');
      }
    } catch (cause) {
      setError(cause?.response?.data?.detail || 'We could not process that request. Check the details and try again.');
    } finally {
      setBusy(false);
    }
  };
  const completedMessage = isReset ? 'Your password was updated. You can now sign in.' : 'If an account exists for that address, reset instructions will arrive by email.';
  return <PublicFrame><main className="auth-special compact"><div className="special-icon"><Mail size={23}/></div><span className="kicker">Account recovery</span><h1>{isReset ? 'Choose a new password.' : 'Reset your password.'}</h1><p>{complete ? completedMessage : isReset ? 'Use the secure link sent to your email to set a new password.' : 'Enter your email and we’ll send you a secure reset link.'}</p>{!complete && <form className="special-form" onSubmit={submit}>{isReset ? <><label>New password<input value={password} onChange={event => setPassword(event.target.value)} type="password" minLength={8} autoComplete="new-password" required/></label><label>Confirm new password<input value={confirmation} onChange={event => setConfirmation(event.target.value)} type="password" minLength={8} autoComplete="new-password" required/></label></> : <label>Email address<input value={email} onChange={event => setEmail(event.target.value)} type="email" autoComplete="email" required placeholder="you@example.com"/></label>}{error && <p className="form-error" role="alert">{error}</p>}<button className="button" type="submit" disabled={busy}>{busy ? 'Working…' : isReset ? 'Update password' : 'Send reset link'} <ArrowRight size={15}/></button></form>}<Link to="/auth/login" className="text-link">Back to login</Link></main></PublicFrame>;
}
