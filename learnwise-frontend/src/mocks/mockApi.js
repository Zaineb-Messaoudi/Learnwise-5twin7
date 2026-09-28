import { activities, courses, weeklyActivity } from '../data/mockData';
const wait = (ms = 180) => new Promise(resolve => window.setTimeout(resolve, ms));
export const mockApi = {
    async getStudentOverview() { await wait(); return { courses, weeklyActivity, activities, stats: { enrolled: 3, completed: 1, score: 87, hours: 12.4 } }; },
    async getCourse(id) { await wait(); return courses.find(course => course.id === id) || courses[0]; },
    async getProgress() { await wait(); return { weeklyActivity, completion: 68, focusAreas: ['Probability & statistics', 'Research synthesis'] }; },
    async submitQuiz(answers) { await wait(350); return { score: Math.min(100, 72 + Object.keys(answers).length * 2), answers }; },
    async uploadMaterial(file) { await wait(500); return { id: crypto.randomUUID(), name: file.name, status: 'completed', progress: 100 }; },
    async askAssistant(content) { await wait(400); return { role: 'assistant', content: `Here is a useful way to think about “${content}”: start with the core idea, then connect it to the example in your course.` }; },
};
