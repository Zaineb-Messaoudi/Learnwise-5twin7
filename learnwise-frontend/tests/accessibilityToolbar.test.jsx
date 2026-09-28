import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AccessibilityToolbar } from '../src/components/ui/AccessibilityToolbar';

describe('AccessibilityToolbar', () => {
  beforeEach(() => window.localStorage.clear());

  test('supports keyboard dismissal and restores focus to its trigger', async () => {
    const user = userEvent.setup();
    render(<AccessibilityToolbar><main>Content</main></AccessibilityToolbar>);
    const trigger = screen.getByRole('button', { name: /open accessibility preferences/i });
    await user.click(trigger);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /high contrast/i }));
    expect(document.documentElement).toHaveClass('a11y-high-contrast');
    await user.keyboard('{Escape}');
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });
});
