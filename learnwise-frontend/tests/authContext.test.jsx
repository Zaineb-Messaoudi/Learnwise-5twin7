import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { AuthProvider, useAuth } from '../src/contexts/AuthContext';

function Probe() {
  const { user, isAuthenticated, login, logout } = useAuth();
  return <div><output>{isAuthenticated ? `${user.name}:${user.role}` : 'signed-out'}</output><button onClick={() => login({ id: 'test', name: 'Test User', role: 'teacher' })}>Sign in</button><button onClick={logout}>Sign out</button></div>;
}

describe('mock authentication state', () => {
  beforeEach(() => window.localStorage.clear());
  it('persists and clears an authenticated role', () => {
    render(<AuthProvider><Probe /></AuthProvider>);
    expect(screen.getByText('signed-out')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));
    expect(screen.getByText('Test User:teacher')).toBeInTheDocument();
    expect(JSON.parse(window.localStorage.getItem('learnwise:user')).role).toBe('teacher');
    fireEvent.click(screen.getByRole('button', { name: 'Sign out' }));
    expect(screen.getByText('signed-out')).toBeInTheDocument();
  });
});
