import { mockApi } from '../src/mocks/mockApi';
describe('mock API', () => {
    it('returns course data', async () => { const result = await mockApi.getCourse('ai-101'); expect(result.title).toBe('AI & Machine Learning'); });
    it('returns deterministic quiz scoring', async () => { const result = await mockApi.submitQuiz({ one: 'a', two: 'b' }); expect(result.score).toBe(76); });
});
