import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AuthProvider } from '../src/contexts/AuthContext';
import { AuthPage } from '../src/features/auth/pages/AuthPage';

jest.mock('../src/api/client', () => ({ isBackendApiEnabled: false }));
jest.mock('../src/api/auth.api', () => ({ authApi: { login: jest.fn(), register: jest.fn() } }));

describe('account access and decorative login art', () => {
  beforeEach(() => window.localStorage.clear());

  test('removes the decorative status badge without changing email sign-in', async () => {
    const user = userEvent.setup();
    render(<MemoryRouter><AuthProvider><AuthPage /></AuthProvider></MemoryRouter>);

    expect(document.querySelector('.auth-visual .auth-live-pill')).not.toBeInTheDocument();
    await user.type(screen.getByLabelText(/email address/i), 'learner@example.com');
    await user.type(screen.getByLabelText(/^password/i), 'secure-pass-123');
    await user.click(screen.getByRole('button', { name: /log in/i }));

    expect(window.localStorage.getItem('learnwise:user')).not.toBeNull();
  });
});
