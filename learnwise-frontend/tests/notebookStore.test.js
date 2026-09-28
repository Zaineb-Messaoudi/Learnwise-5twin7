import { createNotebook, getNotebooks } from '../src/features/student/data/notebookStore';

describe('notebook mock store', () => {
  beforeEach(() => window.localStorage.clear());

  test('persists a newly created notebook for the workspace route', () => {
    const created = createNotebook();
    expect(created[0].title).toBe('Untitled learning notebook');
    expect(getNotebooks()[0].id).toBe(created[0].id);
    expect(getNotebooks()[0].sourceItems).toEqual([]);
  });
});
