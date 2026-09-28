import { routeManifest } from '../src/routes/routeManifest';
describe('route manifest', () => {
    it('contains the full product surface', () => {
        expect(routeManifest.length).toBeGreaterThanOrEqual(70);
        expect(routeManifest).toEqual(expect.arrayContaining(['/student/assistant', '/teacher/materials/upload', '/admin/ai-usage', '/auth/face-login']));
    });
});
