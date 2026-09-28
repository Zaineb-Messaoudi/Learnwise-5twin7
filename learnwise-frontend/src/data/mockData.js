export const courses = [
    { id: 'ai-101', title: 'AI & Machine Learning', category: 'Technology', level: 'Intermediate', progress: 68, lessons: 18, color: 'lilac', icon: '✦', next: 'Neural networks basics', instructor: 'Maya Chen' },
    { id: 'ux-thinking', title: 'Design Thinking', category: 'Creative', level: 'Beginner', progress: 42, lessons: 12, color: 'peach', icon: '◈', next: 'Map your user journey', instructor: 'Noah Williams' },
    { id: 'data-story', title: 'Data Storytelling', category: 'Business', level: 'Intermediate', progress: 15, lessons: 16, color: 'mint', icon: '◌', next: 'Choosing the right chart', instructor: 'Leila Haddad' },
];
export const weeklyActivity = [
    { day: 'Mon', hours: 1.2, score: 76 }, { day: 'Tue', hours: 2.4, score: 82 }, { day: 'Wed', hours: 1.8, score: 88 }, { day: 'Thu', hours: 3.1, score: 91 }, { day: 'Fri', hours: 2.2, score: 87 }, { day: 'Sat', hours: 1.4, score: 94 }, { day: 'Sun', hours: 2.8, score: 90 },
];
export const activities = [
    { icon: '✓', title: 'Completed Neural Networks quiz', meta: 'AI & Machine Learning · 10 min ago', tone: 'green' },
    { icon: '✦', title: 'Asked your AI assistant a question', meta: 'AI & Machine Learning · 2 hours ago', tone: 'purple' },
    { icon: '▶', title: 'Finished lesson 3: User interviews', meta: 'Design Thinking · Yesterday', tone: 'blue' },
    { icon: '★', title: 'Earned the “Quick learner” badge', meta: 'Achievements · 2 days ago', tone: 'orange' },
];
export const navStudent = [
    { label: 'Overview', path: '/student/dashboard', icon: 'grid' }, { label: 'My learning', path: '/student/courses', icon: 'book' }, { label: 'Notebooks', path: '/student/notebooks', icon: 'folder' }, { label: 'AI assistant', path: '/student/assistant', icon: 'spark' }, { label: 'Quizzes', path: '/student/quizzes', icon: 'quiz' }, { label: 'Exercises', path: '/student/exercises', icon: 'target' }, { label: 'Progress', path: '/student/progress', icon: 'chart' },
];
export const navTeacher = [
    { label: 'Overview', path: '/teacher/dashboard', icon: 'grid' }, { label: 'Courses', path: '/teacher/courses', icon: 'book' }, { label: 'Materials', path: '/teacher/materials', icon: 'folder' }, { label: 'AI generation', path: '/teacher/ai-generation', icon: 'spark' }, { label: 'Quizzes', path: '/teacher/quizzes', icon: 'quiz' }, { label: 'Students', path: '/teacher/students', icon: 'users' }, { label: 'Analytics', path: '/teacher/analytics', icon: 'chart' },
];
export const navAdmin = [
    { label: 'Overview', path: '/admin/dashboard', icon: 'grid' }, { label: 'Users', path: '/admin/users', icon: 'users' }, { label: 'Content', path: '/admin/courses', icon: 'book' }, { label: 'Assessments', path: '/admin/quizzes', icon: 'quiz' }, { label: 'AI usage', path: '/admin/ai-usage', icon: 'spark' }, { label: 'Analytics', path: '/admin/analytics', icon: 'chart' }, { label: 'Activity', path: '/admin/activity', icon: 'activity' },
];
