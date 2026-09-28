import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { ThemeProvider } from '../src/contexts/ThemeContext';
import { ResourceWorkspace } from '../src/features/staff/components/ResourceWorkspace';
import { AuthProvider } from '../src/contexts/AuthContext';

jest.mock('../src/api/client', () => ({ apiRequest: jest.fn(), isBackendApiEnabled: false }));
const items = [{ name: 'Example course', meta: 'Demo item', status: 'Active', icon: null }];

function renderWorkspace() {
  return render(
    <AuthProvider><ThemeProvider>
      <MemoryRouter>
        <ResourceWorkspace role="teacher" title="Your courses" description="Demo" resource="course" items={items} />
      </MemoryRouter>
    </ThemeProvider></AuthProvider>
  );
}

describe('staff resource workspace', () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.localStorage.removeItem('learnwise:theme');
  });

  it('creates and persists drafts and reviewed status', async () => {
    const user = userEvent.setup();
    const firstRender = renderWorkspace();

    await user.click(screen.getByRole('button', { name: 'Create course' }));
    expect(screen.getByRole('heading', { name: 'Untitled course 1' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Mark reviewed' }));
    await user.click(screen.getByRole('button', { name: 'Reviewed' }));
    expect(screen.getByText('Untitled course 1')).toBeInTheDocument();

    firstRender.unmount();
    renderWorkspace();
    expect(screen.getByText('Untitled course 1')).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Your courses list' }).querySelector('.resource-status')).toHaveTextContent('Reviewed');
  });
});
