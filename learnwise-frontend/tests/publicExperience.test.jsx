import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SignatureLanding } from '../src/features/public/pages/SignatureLandingPage';
import { EducatorLandingPage } from '../src/features/public/pages/EducatorLandingPage';

const renderWithRouter = element => render(<MemoryRouter>{element}</MemoryRouter>);

describe('public experience interactions', () => {
  test('feature explorer exposes an accessible tab and panel relationship', async () => {
    const user = userEvent.setup();
    renderWithRouter(<SignatureLanding />);
    const practice = screen.getByRole('tab', { name: /practice actively/i });
    expect(practice).toHaveAttribute('aria-controls', 'feature-panel-practice');
    await user.click(practice);
    expect(screen.getByRole('tabpanel')).toHaveAttribute('aria-labelledby', 'feature-tab-practice');
    expect(screen.getByRole('heading', { name: /replace passive scrolling/i })).toBeInTheDocument();
  });

  test('feature tabs move focus with arrow, home, and end keys', async () => {
    const user = userEvent.setup();
    renderWithRouter(<SignatureLanding />);
    const materials = screen.getByRole('tab', { name: /bring materials/i });
    materials.focus();
    await user.keyboard('{ArrowRight}');
    expect(screen.getByRole('tab', { name: /ask your companion/i })).toHaveFocus();
    expect(screen.getByRole('tab', { name: /ask your companion/i })).toHaveAttribute('aria-selected', 'true');
    await user.keyboard('{End}');
    expect(screen.getByRole('tab', { name: /see your signal/i })).toHaveFocus();
    await user.keyboard('{Home}');
    expect(materials).toHaveFocus();
  });

  test('learning example identifies illustrative responses and reflects the question', async () => {
    const user = userEvent.setup();
    renderWithRouter(<SignatureLanding />);
    expect(screen.getByText(/interactive example/i)).toBeInTheDocument();
    expect(screen.queryByText(/companion ready/i)).not.toBeInTheDocument();
    const question = screen.getByRole('textbox', { name: /ask learnwise a question/i });
    await user.clear(question);
    await user.type(question, 'Why does sleep help memory?');
    await user.click(screen.getByRole('button', { name: /show an example response/i }));
    expect(screen.getByText(/this example shows/i)).toBeInTheDocument();
    expect(screen.getByText(/Why does sleep help memory/i)).toBeInTheDocument();
  });

  test('homepage educator metrics are identified as sample data', () => {
    renderWithRouter(<SignatureLanding />);
    expect(screen.getByLabelText(/illustrative dashboard metrics/i)).toHaveTextContent(/illustrative dashboard/i);
  });

  test('homepage does not display internal development-mode labels', () => {
    renderWithRouter(<SignatureLanding />);
    expect(document.body.textContent).not.toMatch(/\b(mock|demo|preview)\b/i);
  });

  test('mobile menu moves focus to navigation and closes on escape', async () => {
    const user = userEvent.setup();
    renderWithRouter(<SignatureLanding />);
    const menu = screen.getByRole('button', { name: /open menu/i });
    await user.click(menu);
    const mobileNavigation = screen.getByRole('navigation', { name: /mobile navigation/i });
    expect(within(mobileNavigation).getByRole('link', { name: /how it works/i })).toHaveFocus();
    await user.keyboard('{Escape}');
    expect(screen.queryByRole('navigation', { name: /mobile navigation/i })).not.toBeInTheDocument();
    expect(menu).toHaveFocus();
  });

  test('educator page labels illustrative metrics and retains product navigation', () => {
    renderWithRouter(<EducatorLandingPage />);
    expect(screen.getByRole('heading', { name: /make the signal/i })).toBeInTheDocument();
    expect(screen.getByText(/24 learners in view/i)).toBeInTheDocument();
    expect(screen.getByText(/illustrative view/i)).toBeInTheDocument();
    expect(screen.getAllByRole('link', { name: /learnwise home/i }).length).toBeGreaterThanOrEqual(1);
  });
});
