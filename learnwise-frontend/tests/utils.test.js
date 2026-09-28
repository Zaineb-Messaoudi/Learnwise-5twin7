import { cn } from '../src/lib/utils';
describe('class utility', () => { it('merges conditional Tailwind classes', () => expect(cn('px-2', false && 'hidden', 'px-4')).toBe('px-4')); });
