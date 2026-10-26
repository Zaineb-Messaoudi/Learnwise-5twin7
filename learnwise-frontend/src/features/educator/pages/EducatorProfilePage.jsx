import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../../../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { User, Mail, Lock, Shield, Camera, Save, AlertCircle, CheckCircle, ArrowRight, X, Loader2, Trash2, Key, Smartphone, Activity, Settings, Upload, ChevronDown, Globe, MessageSquare, GitBranch } from 'lucide-react';
import { authApi } from '../../../api/auth.api';
import { AppShell } from '../../../layouts/AppShell';
import { Button, PageHeader, Card } from '../../../components/shared/Primitives';
import { ErrorState, LoadingState } from '../../../components/ui/States';
import './EducatorProfilePage.css';

export function EducatorProfilePage() {
  const { user, updateProfile, getSocialAccounts, unlinkSocialAccount, uploadAvatar, removeAvatar, getUserSessions, revokeSession, get2FAStatus, loading } = useAuth();
  const navigate = useNavigate();
  const [profileData, setProfileData] = useState({
    first_name: user?.first_name || '',
    last_name: user?.last_name || '',
    username: user?.username || '',
    phone: user?.phone || '',
    bio: user?.bio || '',
  });
  const [profileError, setProfileError] = useState('');
  const [profileSuccess, setProfileSuccess] = useState('');
  
  // Avatar upload
  const [avatarPreview, setAvatarPreview] = useState(user?.avatar_url || null);
  const [avatarUploading, setAvatarUploading] = useState(false);
  const [avatarError, setAvatarError] = useState('');
  const fileInputRef = useRef(null);
  
  // Social accounts
  const [socialAccounts, setSocialAccounts] = useState([]);
  const [socialLoading, setSocialLoading] = useState(false);
  
  // 2FA
  const [twofaStatus, setTwofaStatus] = useState(null);
  const [twofaLoading, setTwofaLoading] = useState(false);
  
  // Sessions
  const [sessions, setSessions] = useState([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  
  useEffect(() => {
    if (user) {
      setProfileData({
        first_name: user.first_name || '',
        last_name: user.last_name || '',
        username: user.username || '',
        phone: user.phone || '',
        bio: user.bio || '',
      });
      loadSocialAccounts();
      load2FAStatus();
      loadSessions();
    }
  }, [user]);
  
  const loadSocialAccounts = async () => {
    setSocialLoading(true);
    try {
      const result = await getSocialAccounts();
      if (result.success) setSocialAccounts(result.data || []);
    } finally { setSocialLoading(false); }
  };
  
  const load2FAStatus = async () => {
    setTwofaLoading(true);
    try {
      const result = await get2FAStatus();
      if (result.success) setTwofaStatus(result.data);
    } finally { setTwofaLoading(false); }
  };
  
  const loadSessions = async () => {
    setSessionsLoading(true);
    try {
      const result = await getUserSessions();
      if (result.success) setSessions(result.data || []);
    } finally { setSessionsLoading(false); }
  };
  
  const handleProfileChange = (e) => {
    const { name, value } = e.target;
    setProfileData(prev => ({ ...prev, [name]: value }));
    setProfileError('');
    setProfileSuccess('');
  };
  
  const handleProfileSubmit = async (e) => {
    e.preventDefault();
    setProfileError('');
    setProfileSuccess('');
    const result = await updateProfile(profileData);
    if (result.success) {
      setProfileSuccess('Profile updated successfully!');
    } else {
      setProfileError(result.error);
    }
  };
  
  const handleAvatarChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    if (!file.type.startsWith('image/')) {
      setAvatarError('Please select an image file');
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setAvatarError('File size must be less than 5MB');
      return;
    }
    
    const reader = new FileReader();
    reader.onload = (e) => {
      setAvatarPreview(e.target.result);
      setAvatarError('');
    };
    reader.readAsDataURL(file);
  };
  
  const handleAvatarUpload = async () => {
    if (!avatarPreview || avatarPreview === user?.avatar_url) return;
    
    setAvatarUploading(true);
    setAvatarError('');
    try {
      const response = await fetch(avatarPreview);
      const blob = await response.blob();
      const file = new File([blob], 'avatar.png', { type: 'image/png' });
      
      const result = await uploadAvatar(file);
      if (result.success) {
        setProfileSuccess('Avatar updated successfully!');
      } else {
        setAvatarError(result.error || 'Upload failed');
      }
    } catch (err) {
      setAvatarError('Upload failed. Please try again.');
    } finally {
      setAvatarUploading(false);
    }
  };
  
  const handleAvatarRemove = async () => {
    if (!window.confirm('Remove your avatar?')) return;
    
    setAvatarError('');
    try {
      const result = await removeAvatar();
      if (result.success) {
        setAvatarPreview(null);
        setProfileSuccess('Avatar removed');
      } else {
        setAvatarError(result.error || 'Failed to remove avatar');
      }
    } catch (err) {
      setAvatarError('Failed to remove avatar');
    }
  };
  
  const handleDragOver = (e) => {
    e.preventDefault();
    e.currentTarget.classList.add('drag-over');
  };
  
  const handleDragLeave = (e) => {
    e.currentTarget.classList.remove('drag-over');
  };
  
  const handleDrop = (e) => {
    e.preventDefault();
    e.currentTarget.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (file) {
      const event = { target: { files: [file] } };
      handleAvatarChange(event);
    }
  };
  
  const handleSocialUnlink = async (provider) => {
    if (!window.confirm(`Unlink ${provider} account?`)) return;
    
    try {
      const result = await unlinkSocialAccount(provider);
      if (result.success) {
        loadSocialAccounts();
      } else {
        alert(result.error || 'Failed to unlink');
      }
    } catch (err) {
      alert('Failed to unlink account');
    }
  };
  
  const handleRevokeSession = async (sessionId) => {
    if (!window.confirm('Revoke this session?')) return;
    try {
      const result = await revokeSession(sessionId);
      if (result.success) loadSessions();
    } catch (err) {
      alert('Failed to revoke session');
    }
  };
  
  const getRoleLabel = (role) => {
    const labels = { etudiant: 'Student', professeur: 'Educator', admin: 'Administrator' };
    return labels[role] || role;
  };
  
  const getInitials = () => {
    if (user?.first_name || user?.last_name) {
      return `${user.first_name?.[0] || ''}${user.last_name?.[0] || ''}`.toUpperCase();
    }
    return user?.email?.[0]?.toUpperCase() || 'U';
  };
  
  const getProviderIcon = (provider) => {
    switch (provider) {
      case 'google': return <Globe size={18} />;
      case 'github': return <GitBranch size={18} />;
      case 'linkedin': return <MessageSquare size={18} />;
      default: return <Globe size={18} />;
    }
  };
  
const getProviderLabel = (provider) => {
    const labels = { google: 'Google', github: 'GitHub', linkedin: 'LinkedIn' };
    return labels[provider] || provider;
  };

  return (
    <AppShell>
      <div className="profile-atlas">
        <PageHeader
          eyebrow="Account"
          title="Profile"
          description="Manage your personal information, connected accounts, and security."
          action={
            <Button variant="ghost" onClick={() => navigate('/teacher/security')}>
              <Settings size={16} /> Security Settings
            </Button>
          }
        />
        
        {/* Profile Header Card */}
        <Card className="profile-header-card">
          <div className="profile-header-content">
            <div className="avatar-section">
              <div className="avatar-upload-area" onDragOver={handleDragOver} onDragLeave={handleDragLeave} onDrop={handleDrop}>
                <input type="file" ref={fileInputRef} accept="image/*" onChange={handleAvatarChange} style={{ display: 'none' }} />
                
                {avatarPreview ? (
                  <img src={avatarPreview} alt="Avatar" className="avatar-large" />
                ) : (
                  <div className="avatar-large placeholder">{getInitials()}</div>
                )}
                
                <label className="avatar-upload-btn" htmlFor="avatar-input">
                  <Upload size={20} />
                  <span>Change</span>
                </label>
                
                <input id="avatar-input" type="file" ref={fileInputRef} accept="image/*" onChange={handleAvatarChange} style={{ display: 'none' }} />
                
                {avatarError && <div className="avatar-error">{avatarError}</div>}
              </div>
            </div>
            
            <div className="header-info">
              <div className="header-meta">
                <h1>{user?.name || user?.email}</h1>
                <div className="meta-row">
                  <span className="role-badge">{getRoleLabel(user?.role)}</span>
                  <span className="email">{user?.email}</span>
                </div>
              </div>
              
              <div className="status-badges">
                {user?.email_verified ? (
                  <span className="badge verified"><Shield size={12} /> Email verified</span>
                ) : (
                  <span className="badge warning"><AlertCircle size={12} /> Email not verified</span>
                )}
                {twofaLoading ? (
                  <span className="badge loading"><Loader2 size={12} className="spin" /> 2FA loading...</span>
                ) : twofaStatus?.enabled ? (
                  <span className="badge success"><Shield size={12} /> 2FA enabled</span>
                ) : (
                  <span className="badge muted"><Shield size={12} /> 2FA disabled</span>
                )}
              </div>
            </div>
            
            <div className="header-actions">
              <Button variant="primary" onClick={handleAvatarUpload} disabled={avatarUploading || !avatarPreview || avatarPreview === user?.avatar_url}>
                {avatarUploading ? <Loader2 size={16} className="spin" /> : 'Save Avatar'}
              </Button>
              {avatarPreview && (
                <Button variant="secondary" onClick={handleAvatarRemove}>
                  <Trash2 size={16} /> Remove
                </Button>
              )}
            </div>
          </div>
        </Card>
        
        {/* Main Content Grid */}
        <div className="profile-grid">
          <main className="main-content">
            {/* Personal Information Card */}
            <Card>
              <div className="card-header">
                <h2><User size={20} /> Personal Information</h2>
              </div>
              <form onSubmit={handleProfileSubmit} className="card-body">
                <div className="form-grid">
                  <div className="form-group">
                    <label htmlFor="first_name">First Name</label>
                    <input
                      id="first_name"
                      name="first_name"
                      type="text"
                      value={profileData.first_name}
                      onChange={handleProfileChange}
                      placeholder="First name"
                    />
                  </div>
                  <div className="form-group">
                    <label htmlFor="last_name">Last Name</label>
                    <input
                      id="last_name"
                      name="last_name"
                      type="text"
                      value={profileData.last_name}
                      onChange={handleProfileChange}
                      placeholder="Last name"
                    />
                  </div>
                </div>
                <div className="form-group">
                  <label htmlFor="username">Username</label>
                  <input
                    id="username"
                    name="username"
                    type="text"
                    value={profileData.username}
                    onChange={handleProfileChange}
                    placeholder="Username"
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="phone">Phone Number</label>
                  <input
                    id="phone"
                    name="phone"
                    type="tel"
                    value={profileData.phone}
                    onChange={handleProfileChange}
                    placeholder="+1 (555) 000-0000"
                  />
                </div>
                <div className="form-group full-width">
                  <label htmlFor="bio">Bio</label>
                  <textarea
                    id="bio"
                    name="bio"
                    value={profileData.bio}
                    onChange={handleProfileChange}
                    placeholder="Tell us about yourself..."
                    rows={4}
                  />
                </div>
                
                {profileError && <div className="form-message error">{profileError}</div>}
                {profileSuccess && <div className="form-message success">{profileSuccess}</div>}
                
                <Button type="submit" disabled={loading}>
                  <Save size={18} /> Save Changes
                </Button>
              </form>
            </Card>
            
            {/* Social Accounts Card */}
            <Card>
              <div className="card-header">
                <h2><Globe size={20} /> Connected Accounts</h2>
                <p className="card-subtitle">Link social accounts for easier sign-in</p>
              </div>
              <div className="card-body">
                {socialLoading ? (
                  <div className="loading-state"><Loader2 size={24} className="spin" /></div>
                ) : socialAccounts.length > 0 ? (
                  <div className="social-list">
                    {socialAccounts.map(account => (
                      <div key={account.id} className="social-item">
                        <div className="social-info">
                          {getProviderIcon(account.provider)}
                          <div>
                            <strong>{getProviderLabel(account.provider)}</strong>
                            <span className="social-email">{account.provider_email || 'Connected'}</span>
                          </div>
                        </div>
                        <button className="btn-danger-sm" onClick={() => handleSocialUnlink(account.provider)}>
                          <Trash2 size={14} /> Unlink
                        </button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="empty-state">
                    <Globe size={32} />
                    <p>No connected accounts</p>
                    <span>Connect social accounts for easier sign-in</span>
                  </div>
                )}
              </div>
            </Card>
            
            {/* Security Overview Card */}
            <Card>
              <div className="card-header">
                <h2><Shield size={20} /> Security Overview</h2>
                <p className="card-subtitle">Manage your account security</p>
              </div>
              <div className="card-body">
                <div className="security-grid">
                  <div className="security-item">
                    <div className="security-icon twofa">{twofaStatus?.enabled ? <Shield size={24} /> : <Key size={24} />}</div>
                    <div>
                      <strong>Two-Factor Authentication</strong>
                      <span>{twofaStatus?.enabled ? 'Enabled' : 'Disabled'}</span>
                    </div>
                  </div>
                  <div className="security-item">
                    <div className="security-icon sessions"><Activity size={24} /></div>
                    <div>
                      <strong>Active Sessions</strong>
                      <span>{sessions.length} active</span>
                    </div>
                  </div>
                  <div className="security-item">
                    <div className="security-icon social">{socialAccounts.length > 0 ? <Globe size={24} /> : <MessageSquare size={24} />}</div>
                    <div>
                      <strong>Connected Accounts</strong>
                      <span>{socialAccounts.length} connected</span>
                    </div>
                  </div>
                </div>
                <div className="security-actions">
                  <Button variant="secondary" onClick={() => navigate('/teacher/security')}>
                    <Settings size={16} /> Manage Security Settings
                    <ChevronDown size={16} />
                  </Button>
                </div>
              </div>
            </Card>
            
            {/* Recent Sessions Card */}
            <Card>
              <div className="card-header">
                <h2><Activity size={20} /> Recent Sessions</h2>
                <p className="card-subtitle">Your active login sessions</p>
              </div>
              <div className="card-body">
                {sessionsLoading ? (
                  <div className="loading-state"><Loader2 size={24} className="spin" /></div>
                ) : sessions.length > 0 ? (
                  <div className="sessions-list-modern">
                    {sessions.slice(0, 3).map(session => (
                      <div key={session.id} className="session-item-modern">
                        <div className="session-info">
                          <div className="session-device">{session.device_name || 'Unknown device'}</div>
                          <div className="session-meta">
                            <span>{session.ip_address || 'Unknown IP'}</span>
                            <span>·</span>
                            <span>{new Date(session.created_at).toLocaleString()}</span>
                            {session.is_current && <span className="current-badge">Current</span>}
                          </div>
                        </div>
                        {!session.is_current && (
                          <button className="btn-ghost-sm" onClick={() => handleRevokeSession(session.id)}>
                            <Trash2 size={14} /> Revoke
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="empty-state">
                    <Activity size={32} />
                    <p>No active sessions</p>
                  </div>
                )}
                <div className="card-footer">
                  <Button variant="secondary" onClick={() => navigate('/teacher/security')}>
                    <ChevronDown size={16} /> View All Sessions
                  </Button>
                </div>
              </div>
            </Card>
          </main>
        </div>
        </div>
      </AppShell>
  );
}