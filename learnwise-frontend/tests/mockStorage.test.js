import { readMock, removeMock, writeMock } from '../src/services/mockStorage';
describe('mock storage', () => {
    beforeEach(() => window.localStorage.clear());
    it('round-trips JSON values', () => { expect(writeMock('progress', { score: 87 })).toEqual({ score: 87 }); expect(readMock('progress', null)).toEqual({ score: 87 }); });
    it('returns fallback for missing keys and removes values', () => { expect(readMock('missing', ['empty'])).toEqual(['empty']); writeMock('x', 1); removeMock('x'); expect(readMock('x', 0)).toBe(0); });
});
