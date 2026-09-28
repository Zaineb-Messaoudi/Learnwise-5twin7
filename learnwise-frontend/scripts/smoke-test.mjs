const base = process.env.BASE_URL || 'http://localhost:5173'
const routes = [
  '/', '/about', '/features', '/how-it-works', '/educators', '/terms', '/privacy', '/contact', '/faq', '/auth/login', '/auth/register', '/auth/forgot-password', '/auth/reset-password', '/auth/verify', '/auth/face-login',
  '/student/dashboard', '/student/search', '/student/notebooks', '/student/notebooks/neural-networks', '/student/courses', '/student/courses/ai-101', '/student/courses/ai-101/player', '/student/assistant', '/student/assistant/demo', '/student/voice-question', '/student/quizzes', '/student/quizzes/demo', '/student/quizzes/demo/attempt', '/student/quizzes/demo/result', '/student/exercises', '/student/exercises/demo', '/student/learning-path', '/student/progress', '/student/performance', '/student/achievements', '/student/sessions', '/student/activity', '/student/notifications', '/student/profile', '/student/settings',
  '/teacher/dashboard', '/teacher/courses', '/teacher/courses/new', '/teacher/courses/demo', '/teacher/courses/demo/edit', '/teacher/materials', '/teacher/materials/upload', '/teacher/audio-processing', '/teacher/pdf-processing', '/teacher/transcriptions', '/teacher/summaries', '/teacher/ai-generation', '/teacher/quizzes', '/teacher/questions', '/teacher/exercises', '/teacher/students', '/teacher/students/demo', '/teacher/analytics', '/teacher/profile', '/teacher/settings',
  '/admin/dashboard', '/admin/users', '/admin/users/demo', '/admin/students', '/admin/teachers', '/admin/courses', '/admin/quizzes', '/admin/exercises', '/admin/ai-usage', '/admin/analytics', '/admin/activity', '/admin/notifications', '/admin/settings', '/403', '/404', '/500'
]
const results = await Promise.all(routes.map(async route => {
  const response = await fetch(`${base}${route}`)
  return { route, status: response.status, ok: response.ok }
}))
const failed = results.filter(result => !result.ok)
console.log(`Smoke tested ${results.length} routes: ${results.length - failed.length} passed, ${failed.length} failed`)
if (failed.length) { console.error(failed); process.exit(1) }
