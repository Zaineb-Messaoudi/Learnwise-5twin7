import React, { useState, useEffect, useMemo } from 'react';
import { authApi } from '../../../../api/auth.api';
import { Search, Filter, MoreVertical, Shield, UserX, UserCheck, Trash2, Edit, Mail, AlertCircle, CheckCircle, Loader2, ChevronLeft, ChevronRight } from 'lucide-react';
import './AdminUserManagement.css';

export function AdminUserManagement() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [pageSize] = useState(20);
  const [stats, setStats] = useState(null);
  const [selectedUser, setSelectedUser] = useState(null);
  const [actionLoading, setActionLoading] = useState(null);
  const [showUserModal, setShowUserModal] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [editForm, setEditForm] = useState({});

  const fetchUsers = async () => {
    setLoading(true);
    setError('');
    try {
      const params = {
        page: currentPage,
        page_size: pageSize,
        search: search || undefined,
        role: roleFilter !== 'all' ? roleFilter : undefined,
        is_active: statusFilter !== 'all' ? statusFilter === 'active' : undefined,
      };
      const response = await authApi.adminListUsers(params);
      setUsers(response.results || response);
      setTotalCount(response.count || response.length);
      setTotalPages(Math.ceil((response.count || response.length) / pageSize));
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to load users.');
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await authApi.adminGetStats();
      setStats(response);
    } catch {
      // Ignore stats errors
    }
  };

  useEffect(() => {
    fetchUsers();
    fetchStats();
  }, [currentPage, search, roleFilter, statusFilter]);

  const handleAction = async (userId, action) => {
    setActionLoading(userId);
    try {
      let result;
      switch (action) {
        case 'activate':
          result = await authApi.adminActivateUser(userId);
          break;
        case 'deactivate':
          result = await authApi.adminDeactivateUser(userId);
          break;
        case 'make_admin':
          result = await authApi.adminMakeAdmin(userId);
          break;
        case 'remove_admin':
          result = await authApi.adminRemoveAdmin(userId);
          break;
        default:
          return;
      }
      if (result.success !== false) {
        fetchUsers();
        fetchStats();
      }
    } catch (err) {
      setError(err?.response?.data?.detail || `Failed to ${action} user.`);
    } finally {
      setActionLoading(null);
    }
  };

  const handleEdit = (user) => {
    setEditingUser(user);
    setEditForm({
      email: user.email,
      username: user.username,
      first_name: user.first_name || '',
      last_name: user.last_name || '',
      role: user.role,
      is_active: user.is_active,
      is_staff: user.is_staff,
    });
    setShowUserModal(true);
  };

  const handleSaveEdit = async () => {
    if (!editingUser) return;
    setActionLoading(editingUser.id);
    try {
      await authApi.adminUpdateUser(editingUser.id, editForm);
      fetchUsers();
      fetchStats();
      setShowUserModal(false);
      setEditingUser(null);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to update user.');
    } finally {
      setActionLoading(null);
    }
  };

  const getRoleBadge = (role) => {
    const badges = {
      etudiant: { label: 'Student', class: 'role-student' },
      professeur: { label: 'Educator', class: 'role-teacher' },
      admin: { label: 'Admin', class: 'role-admin' },
    };
    return badges[role] || { label: role, class: '' };
  };

  const filteredUsers = useMemo(() => users, [users]);

  return (
    <div className="admin-users-page">
      <div className="page-header">
        <div>
          <h1>User Management</h1>
          <p>Manage platform users, roles, and permissions</p>
        </div>
        {stats && (
          <div className="stats-summary">
            <div className="stat-item">
              <span className="stat-value">{stats.total}</span>
              <span className="stat-label">Total Users</span>
            </div>
            <div className="stat-item">
              <span className="stat-value">{stats.students}</span>
              <span className="stat-label">Students</span>
            </div>
            <div className="stat-item">
              <span className="stat-value">{stats.teachers}</span>
              <span className="stat-label">Educators</span>
            </div>
            <div className="stat-item">
              <span className="stat-value">{stats.admins}</span>
              <span className="stat-label">Admins</span>
            </div>
            <div className="stat-item">
              <span className="stat-value">{stats.active}</span>
              <span className="stat-label">Active</span>
            </div>
            <div className="stat-item">
              <span className="stat-value">{stats.verified}</span>
              <span className="stat-label">Verified</span>
            </div>
          </div>
        )}
      </div>

      <div className="filters-bar">
        <div className="search-box">
          <Search size={18} />
          <input
            type="text"
            placeholder="Search users by name, email, username..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setCurrentPage(1); }}
          />
        </div>
        <div className="filter-group">
          <select
            value={roleFilter}
            onChange={(e) => { setRoleFilter(e.target.value); setCurrentPage(1); }}
          >
            <option value="all">All Roles</option>
            <option value="etudiant">Students</option>
            <option value="professeur">Educators</option>
            <option value="admin">Admins</option>
          </select>
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setCurrentPage(1); }}
          >
            <option value="all">All Status</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
        </div>
      </div>

      {error && <div className="error-banner">{error} <button onClick={() => setError('')}>×</button></div>}

      <div className="table-container">
        {loading ? (
          <div className="loading-state">
            <Loader2 className="spin" size={32} />
            <p>Loading users...</p>
          </div>
        ) : filteredUsers.length === 0 ? (
          <div className="empty-state">
            <UserX size={48} />
            <h3>No users found</h3>
            <p>Try adjusting your filters or search terms.</p>
          </div>
        ) : (
          <table className="users-table">
            <thead>
              <tr>
                <th>User</th>
                <th>Role</th>
                <th>Status</th>
                <th>Email Verified</th>
                <th>Joined</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredUsers.map(user => (
                <tr key={user.id}>
                  <td>
                    <div className="user-cell">
                      <div className="user-avatar">{user.name?.[0]?.toUpperCase() || user.email[0].toUpperCase()}</div>
                      <div className="user-info">
                        <span className="user-name">{user.name || user.email}</span>
                        <span className="user-email">{user.email}</span>
                        {user.username && <span className="user-username">@{user.username}</span>}
                      </div>
                    </div>
                  </td>
                  <td>
                    <span className={`role-badge ${getRoleBadge(user.role).class}`}>
                      {getRoleBadge(user.role).label}
                    </span>
                  </td>
                  <td>
                    <span className={`status-badge ${user.is_active ? 'active' : 'inactive'}`}>
                      {user.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td>
                    <span className={`verified-badge ${user.email_verified ? 'verified' : 'unverified'}`}>
                      {user.email_verified ? (
                        <>
                          <CheckCircle size={14} /> Verified
                        </>
                      ) : (
                        <>
                          <AlertCircle size={14} /> Pending
                        </>
                      )}
                    </span>
                  </td>
                  <td>{user.date_joined ? new Date(user.date_joined).toLocaleDateString() : '-'}</td>
                  <td>
                    <div className="action-menu">
                      <button className="action-trigger" onClick={(e) => { e.stopPropagation(); setSelectedUser(user.id === selectedUser ? null : user.id); }}>
                        <MoreVertical size={18} />
                      </button>
                      {selectedUser === user.id && (
                        <div className="action-dropdown" onClick={(e) => e.stopPropagation()}>
                          <button onClick={() => handleEdit(user)}>
                            <Edit size={16} /> Edit
                          </button>
                          {user.is_active ? (
                            <button onClick={() => handleAction(user.id, 'deactivate')} className="danger">
                              <UserX size={16} /> Deactivate
                            </button>
                          ) : (
                            <button onClick={() => handleAction(user.id, 'activate')}>
                              <UserCheck size={16} /> Activate
                            </button>
                          )}
                          {user.role !== 'admin' ? (
                            <button onClick={() => handleAction(user.id, 'make_admin')}>
                              <Shield size={16} /> Make Admin
                            </button>
                          ) : (
                            <button onClick={() => handleAction(user.id, 'remove_admin')} className="danger">
                              <Shield size={16} /> Remove Admin
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {totalPages > 1 && (
            <div className="pagination">
              <button onClick={() => setCurrentPage(p => Math.max(1, p - 1))} disabled={currentPage === 1}>
                <ChevronLeft size={18} />
              </button>
              <span className="page-info">Page {currentPage} of {totalPages} ({totalCount} users)</span>
              <button onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))} disabled={currentPage === totalPages}>
                <ChevronRight size={18} />
              </button>
            </div>
          )}
        )}
      </div>

      {showUserModal && editingUser && (
        <div className="modal-overlay" onClick={() => setShowUserModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Edit User</h2>
              <button onClick={() => setShowUserModal(false)}>&times;</button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label>Email</label>
                <input
                  type="email"
                  value={editForm.email}
                  onChange={e => setEditForm(prev => ({ ...prev, email: e.target.value }))}
                />
              </div>
              <div className="form-group">
                <label>Username</label>
                <input
                  type="text"
                  value={editForm.username}
                  onChange={e => setEditForm(prev => ({ ...prev, username: e.target.value }))}
                />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>First Name</label>
                  <input
                    type="text"
                    value={editForm.first_name}
                    onChange={e => setEditForm(prev => ({ ...prev, first_name: e.target.value }))}
                  />
                </div>
                <div className="form-group">
                  <label>Last Name</label>
                  <input
                    type="text"
                    value={editForm.last_name}
                    onChange={e => setEditForm(prev => ({ ...prev, last_name: e.target.value }))}
                  />
                </div>
              </div>
              <div className="form-group">
                <label>Role</label>
                <select
                  value={editForm.role}
                  onChange={e => setEditForm(prev => ({ ...prev, role: e.target.value }))}
                >
                  <option value="etudiant">Student</option>
                  <option value="professeur">Educator</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <div className="form-row">
                <div className="form-group checkbox-group">
                  <label>
                    <input
                      type="checkbox"
                      checked={editForm.is_active}
                      onChange={e => setEditForm(prev => ({ ...prev, is_active: e.target.checked }))}
                    />
                    Active
                  </label>
                </div>
                <div className="form-group checkbox-group">
                  <label>
                    <input
                      type="checkbox"
                      checked={editForm.is_staff}
                      onChange={e => setEditForm(prev => ({ ...prev, is_staff: e.target.checked }))}
                    />
                    Staff
                  </label>
                </div>
              </div>
            </div>
            <div className="modal-footer">
              <button onClick={() => setShowUserModal(false)} className="btn-secondary">Cancel</button>
              <button onClick={handleSaveEdit} className="btn-primary" disabled={actionLoading === editingUser.id}>
                {actionLoading === editingUser.id ? <Loader2 size={16} /> : 'Save Changes'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}