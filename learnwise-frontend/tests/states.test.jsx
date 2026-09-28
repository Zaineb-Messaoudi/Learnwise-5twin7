import { render, screen } from '@testing-library/react';
import { ErrorState, EmptyState, LoadingState } from '../src/components/ui/States';
describe('async state components', () => {
    it('exposes loading and error semantics', () => { render(<><LoadingState label="Loading courses"/><ErrorState message="Network unavailable"/></>); expect(screen.getByRole('status')).toHaveTextContent('Loading courses'); expect(screen.getByRole('alert')).toHaveTextContent('Network unavailable'); });
    it('renders an empty-state action', () => { render(<EmptyState title="No courses yet" action={<button>Create course</button>}/>); expect(screen.getByText('No courses yet')).toBeInTheDocument(); expect(screen.getByRole('button', { name: 'Create course' })).toBeInTheDocument(); });
});
