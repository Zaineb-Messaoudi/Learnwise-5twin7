import React, { useState, useEffect } from 'react';
import { Shield, Key, Smartphone, Clock, Activity, History, AlertTriangle, LogOut, CheckCircle, Copy, QrCode as QrCodeIcon, Trash2 } from 'lucide-react';
import { useAuth } from '../../../contexts/AuthContext';
import { authApi } from '../../../api/auth.api';
import { AppShell } from '../../../layouts/AppShell';
import './SecuritySettingsPage.css';

export function SecuritySettingsPage() {
  const {
    user,
    changePassword,
    updateProfile,
    get2FASetup,
    enable2FA,
    disable2FA,
    listSessions,
    revokeSession,
    revokeAllSessions,
    getSecurityEvents,
    getDataExports,
    requestDataExport,
    getDeletionRequest,
    requestAccountDeletion,
    confirmAccountDeletion,
    cancelAccountDeletion,
    getTerms,
    acceptTerms,
    loading,
    error,
    clearError,
    stepUpRequired,
    stepUpError,
    stepUpWithPassword,
    clearStepUp,
  } = useAuth();

  const [activeTab, setActiveTab] = useState('password');
  const [passwordForm, setPasswordForm] = useState({ current_password: '', new_password: '', confirm_password: '' });
  const [twofaStep, setTwofaStep] = useState('status');
  const [twofaData, setTwofaData] = useState(null);
  const [totpToken, setTotpToken] = useState('');
  const [backupCode, setBackupCode] = useState('');
  const [sessions, setSessions] = useState([]);
  const [securityEvents, setSecurityEvents] = useState([]);
  const [dataExports, setDataExports] = useState([]);
  const [deletionRequest, setDeletionRequest] = useState(null);
  const [deletionForm, setDeletionForm] = useState({ reason: '', feedback: '', password: '', token: '' });
  const [localError, setLocalError] = useState('');
  const [localSuccess, setLocalSuccess] = useState('');
  // Step-up re-authentication: a face-authenticated session cannot perform sensitive
  // operations until the user re-authenticates with a password.
  const [stepUpPassword, setStepUpPassword] = useState('');
  const [stepUpAction, setStepUpAction] = useState(null); // 'changePassword' | 'disable2FA' | 'requestDeletion' | 'confirmDeletion'

  const handleDownloadExport = async (exportId) => {
    setLocalError('');
    try {
      const blob = await authApi.downloadDataExport(exportId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `learnwise-export-${exportId}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (cause) {
      setLocalError(cause?.response?.data?.detail || 'Failed to download export.');
    }
  };

  useEffect(() => {
    loadSecurityData();
  }, []);

  const loadSecurityData = async () => {
    const sessionsResult = await listSessions();
    if (sessionsResult.success) setSessions(sessionsResult.data || []);

    const eventsResult = await getSecurityEvents();
    if (eventsResult.success) setSecurityEvents(eventsResult.data || []);

    const exportsResult = await getDataExports();
    if (exportsResult.success) setDataExports(exportsResult.data || []);

    const deletionResult = await getDeletionRequest();
    if (deletionResult.success) setDeletionRequest(deletionResult.data || null);
  };

  const handlePasswordChange = async (e) => {
    e.preventDefault();
    setLocalError('');
    setLocalSuccess('');
    const result = await changePassword(passwordForm);
    if (result.success) {
      setLocalSuccess('Password changed successfully.');
      setPasswordForm({ current_password: '', new_password: '', confirm_password: '' });
    } else if (result.requiresStepUp) {
      setStepUpAction('changePassword');
      setLocalError(result.error || stepUpError || 'Please re-authenticate with your password.');
    } else {
      setLocalError(result.error);
    }
  };

  const handle2FASetup = async () => {
    setLocalError('');
    const result = await get2FASetup();
    if (result.success) {
      setTwofaData(result.data);
      setTwofaStep('verify');
    } else {
      setLocalError(result.error);
    }
  };

  const handle2FAVerify = async (e) => {
    e.preventDefault();
    setLocalError('');
    const result = await enable2FA({ token: totpToken, backup_code: backupCode });
    if (result.success) {
      setLocalSuccess('Two-factor authentication enabled. Please save your backup codes.');
      setTwofaStep('backup_codes');
      setTwofaData({ ...twofaData, backup_codes: result.backupCodes });
    } else {
      setLocalError(result.error);
    }
  };

  const handle2FADisable = async (e) => {
    e.preventDefault();
    setLocalError('');
    const password = e.target.elements.password.value;
    const result = await disable2FA({ password, token: totpToken, backup_code: backupCode });
    if (result.success) {
      setLocalSuccess('Two-factor authentication disabled.');
      setTwofaStep('status');
      setTotpToken('');
      setBackupCode('');
    } else if (result.requiresStepUp) {
      setStepUpAction('disable2FA');
      setLocalError(result.error || stepUpError || 'Please re-authenticate with your password.');
    } else {
      setLocalError(result.error);
    }
  };

  const handleRevokeAllSessions = async () => {
    if (!window.confirm('Are you sure you want to revoke all other sessions?')) return;
    const result = await revokeAllSessions();
    if (result.success) {
      setLocalSuccess('All sessions revoked.');
      setSessions([]);
    } else {
      setLocalError(result.error);
    }
  };

  const handleRequestExport = async () => {
    const result = await requestDataExport();
    if (result.success) {
      setLocalSuccess('Data export requested. You will receive a download link via email.');
    } else {
      setLocalError(result.error);
    }
  };

  const handleRequestDeletion = async (e) => {
    e.preventDefault();
    setLocalError('');
    const result = await requestAccountDeletion({
      reason: deletionForm.reason,
      feedback: deletionForm.feedback,
    });
    if (result.success) {
      setLocalSuccess(result.message);
      loadSecurityData();
    } else if (result.requiresStepUp) {
      setStepUpAction('requestDeletion');
      setLocalError(result.error || stepUpError || 'Please re-authenticate with your password.');
    } else {
      setLocalError(result.error);
    }
  };

  const handleCancelDeletion = async () => {
    const result = await cancelAccountDeletion();
    if (result.success) {
      setLocalSuccess('Account deletion cancelled.');
      setDeletionRequest(null);
    } else {
      setLocalError(result.error);
    }
  };

  const handleConfirmDeletion = async (e) => {
    e.preventDefault();
    setLocalError('');
    const result = await confirmAccountDeletion({
      token: deletionRequest.confirmation_token,
      password: deletionForm.password,
    });
    if (result.success) {
      setLocalSuccess('Account will be permanently deleted on the scheduled date.');
      loadSecurityData();
    } else if (result.requiresStepUp) {
      setStepUpAction('confirmDeletion');
      setLocalError(result.error || stepUpError || 'Please re-authenticate with your password.');
    } else {
      setLocalError(result.error);
    }
  };

  const handleStepUpSubmit = async (e) => {
    e.preventDefault();
    setLocalError('');
    const result = await stepUpWithPassword(stepUpPassword);
    if (result.success) {
      setStepUpAction(null);
      setStepUpPassword('');
      setLocalSuccess('Re-authenticated with your password. Please try your action again.');
      clearStepUp();
    } else {
      setLocalError(result.error || 'Step-up authentication failed.');
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
  };

  const getInitials = () => {
    if (user?.first_name || user?.last_name) {
      return `${user.first_name?.[0] || ''}${user.last_name?.[0] || ''}`.toUpperCase();
    }
    return user?.email?.[0]?.toUpperCase() || 'U';
  };

  return (
    <AppShell>
      <div className="security-page">
      <div className="security-header">
        <div className="security-avatar">{getInitials()}</div>
        <div className="security-user-info">
          <h1>Security Settings</h1>
          <p>Manage your account security, 2FA, sessions, and data</p>
        </div>
      </div>

      <div className="security-tabs">
        <button className={activeTab === 'password' ? 'active' : ''} onClick={() => setActiveTab('password')}>
          <Key size={18} /> Password
        </button>
        <button className={activeTab === 'twofa' ? 'active' : ''} onClick={() => setActiveTab('twofa')}>
          <Shield size={18} /> Two-Factor Auth
        </button>
        <button className={activeTab === 'sessions' ? 'active' : ''} onClick={() => setActiveTab('sessions')}>
          <Clock size={18} /> Sessions
        </button>
        <button className={activeTab === 'events' ? 'active' : ''} onClick={() => setActiveTab('events')}>
          <Activity size={18} /> Security Events
        </button>
        <button className={activeTab === 'privacy' ? 'active' : ''} onClick={() => setActiveTab('privacy')}>
          <Trash2 size={18} /> Privacy
        </button>
      </div>

      {localError && <div className="security-error">{localError}</div>}
      {localSuccess && <div className="security-success">{localSuccess}</div>}

      {/* Step-up re-authentication prompt (shown when a face-authenticated session
          attempts a sensitive operation that requires a password step-up). */}
      {stepUpAction && (
        <div className="security-section step-up-card">
          <h2>Re-authenticate</h2>
          <p>
            {stepUpError ||
              'This action requires your password. Please re-authenticate to continue.'}
          </p>
          <form onSubmit={handleStepUpSubmit} className="security-form">
            <div className="form-group">
              <label>Password</label>
              <input
                type="password"
                value={stepUpPassword}
                onChange={(e) => setStepUpPassword(e.target.value)}
                placeholder="Enter your password"
                required
                autoComplete="current-password"
              />
            </div>
            <div className="form-actions">
              <button type="submit" className="btn-primary" disabled={loading || !stepUpPassword}>
                Re-authenticate
              </button>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => {
                  setStepUpAction(null);
                  setStepUpPassword('');
                  clearStepUp();
                }}
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Password Tab */}
      {activeTab === 'password' && (
        <div className="security-section">
          <h2>Change Password</h2>
          <form onSubmit={handlePasswordChange} className="security-form">
            <div className="form-group">
              <label>Current Password</label>
              <input
                type="password"
                value={passwordForm.current_password}
                onChange={e => setPasswordForm({ ...passwordForm, current_password: e.target.value })}
                placeholder="Enter current password"
                required
              />
            </div>
            <div className="form-group">
              <label>New Password</label>
              <input
                type="password"
                value={passwordForm.new_password}
                onChange={e => setPasswordForm({ ...passwordForm, new_password: e.target.value })}
                placeholder="At least 8 characters"
                minLength={8}
                required
              />
            </div>
            <div className="form-group">
              <label>Confirm New Password</label>
              <input
                type="password"
                value={passwordForm.confirm_password}
                onChange={e => setPasswordForm({ ...passwordForm, confirm_password: e.target.value })}
                placeholder="Repeat new password"
                minLength={8}
                required
              />
            </div>
            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? 'Working...' : 'Update Password'}
            </button>
          </form>
        </div>
      )}

      {/* Two-Factor Auth Tab */}
      {activeTab === 'twofa' && (
        <div className="security-section">
          <h2>Two-Factor Authentication</h2>

          {twofaStep === 'status' && (
            <>
              {user?.two_factor_enabled ? (
                <div className="twofa-status enabled">
                  <CheckCircle size={24} />
                  <span>2FA is enabled</span>
                  <button className="btn-secondary" onClick={() => setTwofaStep('disable')}>
                    Disable 2FA
                  </button>
                </div>
              ) : (
                <div className="twofa-status disabled">
                  <Shield size={24} />
                  <span>2FA is not enabled</span>
                  <button className="btn-primary" onClick={handle2FASetup}>
                    Enable 2FA
                  </button>
                </div>
              )}
            </>
          )}

          {twofaStep === 'verify' && twofaData && (
            <div className="twofa-setup">
              <div className="qr-code">
                <img src={twofaData.qr_code} alt="QR Code for 2FA" />
              </div>
              <p>Scan this QR code with your authenticator app, then enter the 6-digit code below.</p>
              <form onSubmit={handle2FAVerify} className="twofa-form">
                <div className="form-group">
                  <label>Authentication Code</label>
                  <input
                    type="text"
                    value={totpToken}
                    onChange={e => setTotpToken(e.target.value)}
                    placeholder="6-digit code from authenticator"
                    maxLength={6}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Backup Code (optional)</label>
                  <input
                    type="text"
                    value={backupCode}
                    onChange={e => setBackupCode(e.target.value)}
                    placeholder="Use a backup code instead"
                    maxLength={32}
                  />
                </div>
                <button type="submit" className="btn-primary" disabled={loading}>
                  {loading ? 'Verifying...' : 'Verify & Enable'}
                </button>
              </form>
            </div>
          )}

          {twofaStep === 'backup_codes' && twofaData && (
            <div className="backup-codes">
              <h3>Your Backup Codes</h3>
              <p>Save these codes in a secure place. They can be used to log in if you lose access to your authenticator.</p>
              <div className="code-grid">
                {twofaData.backup_codes?.map((code, i) => (
                  <div key={i} className="backup-code">
                    <span>{code}</span>
                    <button onClick={() => copyToClipboard(code)}>
                      <Copy size={16} />
                    </button>
                  </div>
                ))}
              </div>
              <button className="btn-primary" onClick={() => {
                setTwofaStep('status');
                setTwofaData(null);
              }}>
                Done
              </button>
            </div>
          )}

          {twofaStep === 'disable' && (
            <div className="twofa-disable">
              <h3>Verify Password to Disable 2FA</h3>
              <form onSubmit={handle2FADisable} className="twofa-form">
                <div className="form-group">
                  <label>Current Password</label>
                  <input type="password" name="password" placeholder="Enter your password" required />
                </div>
                <div className="form-group">
                  <label>TOTP Token (if available)</label>
                  <input
                    type="text"
                    value={totpToken}
                    onChange={e => setTotpToken(e.target.value)}
                    placeholder="6-digit code"
                    maxLength={6}
                  />
                </div>
                <div className="form-group">
                  <label>Backup Code (alternative)</label>
                  <input
                    type="text"
                    value={backupCode}
                    onChange={e => setBackupCode(e.target.value)}
                    placeholder="Use a backup code instead"
                    maxLength={32}
                  />
                </div>
                <button type="submit" className="btn-primary" disabled={loading}>
                  {loading ? 'Disabling...' : 'Disable 2FA'}
                </button>
              </form>
            </div>
          )}
        </div>
      )}

      {/* Sessions Tab */}
      {activeTab === 'sessions' && (
        <div className="security-section">
          <h2>Active Sessions</h2>
          <div className="sessions-list">
            {sessions.length === 0 ? (
              <p>No active sessions found.</p>
            ) : (
              sessions.map(session => (
                <div key={session.id} className="session-item">
                  <div className="session-info">
                    <div className="session-device">{session.device_name || 'Unknown device'}</div>
                    <div className="session-details">
                      <span>{session.ip_address || 'Unknown IP'} · {new Date(session.created_at).toLocaleString()}</span>
                    </div>
                    {session.is_current && <span className="session-badge current">Current</span>}
                  </div>
                  {!session.is_current && (
                    <button className="btn-danger" onClick={() => revokeSession(session.id)}>
                      Revoke
                    </button>
                  )}
                </div>
              ))
            )}
          </div>
          {sessions.length > 1 && (
            <button className="btn-secondary" onClick={handleRevokeAllSessions}>
              Revoke All Sessions
            </button>
          )}
        </div>
      )}

      {/* Security Events Tab */}
      {activeTab === 'events' && (
        <div className="security-section">
          <h2>Recent Security Events</h2>
          <div className="events-list">
            {securityEvents.length === 0 ? (
              <p>No security events recorded.</p>
            ) : (
              securityEvents.map(event => (
                <div key={event.id} className={`event-item severity-${event.severity}`}>
                  <div className="event-icon">
                    {event.severity === 'critical' && <AlertTriangle size={20} />}
                    {event.severity === 'warning' && <AlertTriangle size={20} />}
                    {event.severity === 'info' && <Activity size={20} />}
                  </div>
                  <div className="event-info">
                    <span className="event-type">{event.event_type.replace(/_/g, ' ')}</span>
                    {event.description && <p className="event-description">{event.description}</p>}
                    {event.ip_address && <span className="event-ip">{event.ip_address}</span>}
                  </div>
                  <span className="event-time">{new Date(event.created_at).toLocaleString()}</span>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Privacy Tab */}
      {activeTab === 'privacy' && (
        <div className="security-section">
          <h2>Data & Privacy</h2>

          <div className="privacy-section">
            <h3>Data Export</h3>
            <p>Request a copy of your personal data that Learnwise stores about you.</p>
            <button className="btn-primary" onClick={handleRequestExport} disabled={loading}>
              Request Data Export
            </button>
            {dataExports.length > 0 && (
              <div className="exports-list">
                <h4>Export Requests</h4>
                {dataExports.map(exp => (
                  <div key={exp.id} className="export-item">
                    <span>Status: {exp.status}</span>
                    <span>Requested: {new Date(exp.requested_at).toLocaleString()}</span>
                    <button
                      onClick={() => handleDownloadExport(exp.id)}
                      className="text-link"
                    >
                      Download
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="privacy-section">
            <h3>Account Deletion</h3>
            {deletionRequest ? (
              <div className="deletion-status">
                <p>Deletion status: <strong>{deletionRequest.status}</strong></p>
                {deletionRequest.scheduled_deletion_at && (
                  <p>Scheduled for deletion: {new Date(deletionRequest.scheduled_deletion_at).toLocaleString()}</p>
                )}
                {deletionRequest.status === 'pending' && (
                  <>
                    <form onSubmit={handleConfirmDeletion} className="security-form">
                      <div className="form-group">
                        <label>Password to confirm</label>
                        <input
                          type="password"
                          value={deletionForm.password}
                          onChange={e => setDeletionForm({ ...deletionForm, password: e.target.value })}
                          required
                        />
                      </div>
                      <button type="submit" className="btn-primary" disabled={loading}>
                        Confirm Deletion
                      </button>
                      <button type="button" className="btn-secondary" onClick={handleCancelDeletion}>
                        Cancel Deletion
                      </button>
                    </form>
                  </>
                )}
              </div>
            ) : (
              <form onSubmit={handleRequestDeletion} className="security-form">
                <p>Deleting your account will permanently remove all your data. This action cannot be undone.</p>
                <div className="form-group">
                  <label>Reason (optional)</label>
                  <textarea
                    value={deletionForm.reason}
                    onChange={e => setDeletionForm({ ...deletionForm, reason: e.target.value })}
                    placeholder="Help us improve..."
                    rows={3}
                  />
                </div>
                <div className="form-group">
                  <label>Feedback (optional)</label>
                  <textarea
                    value={deletionForm.feedback}
                    onChange={e => setDeletionForm({ ...deletionForm, feedback: e.target.value })}
                    placeholder="Any additional feedback..."
                    rows={3}
                  />
                </div>
                <button type="submit" className="btn-danger" disabled={loading}>
                  Request Account Deletion
                </button>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
    </AppShell>
  );
}