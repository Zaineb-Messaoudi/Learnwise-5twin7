import React, { lazy, useEffect } from 'react';
import { Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
const NotFound = lazy(() => import('../features/auth/pages/NotFoundPage').then(module => ({ default: module.NotFound })));
const SignatureLanding = lazy(() => import('../features/public/pages/SignatureLandingPage').then(module => ({ default: module.SignatureLanding })));
const AtlasDashboardPage = lazy(() => import('../features/student/pages/AtlasDashboardPage').then(module => ({ default: module.AtlasDashboardPage })));
const LearningPathPage = lazy(() => import('../features/student/pages/LearningPathPage').then(module => ({ default: module.LearningPathPage })));
const Landing = lazy(() => import('../pages/PublicPages').then(module => ({ default: module.Landing })));
const PublicSectionPage = lazy(() => import('../pages/PublicPages').then(module => ({ default: module.PublicSectionPage })));
const AuthPage = lazy(() => import('../features/auth/pages/AuthPage').then(module => ({ default: module.AuthPage })));
const FaceCapturePage = lazy(() => import('../features/auth/pages/FaceCapturePage').then(module => ({ default: module.FaceCapturePage })));
const CompleteProfilePage = lazy(() => import('../features/auth/pages/CompleteProfilePage').then(module => ({ default: module.CompleteProfilePage })));
const SocialCallbackPage = lazy(() => import('../features/auth/pages/SocialCallbackPage').then(module => ({ default: module.SocialCallbackPage })));
const LegalPage = lazy(() => import('../features/public/pages/LegalPage').then(module => ({ default: module.LegalPage })));
const EducatorLandingPage = lazy(() => import('../features/public/pages/EducatorLandingPage').then(module => ({ default: module.EducatorLandingPage })));
const StudentDashboard = lazy(() => import('../features/student/pages/StudentDashboard').then(module => ({ default: module.StudentDashboard })));
const CoursesPage = lazy(() => import('../features/student/pages/CoursesPage').then(module => ({ default: module.CoursesPage })));
const AssistantPage = lazy(() => import('../features/student/pages/AssistantPage').then(module => ({ default: module.AssistantPage })));
const VoicePage = lazy(() => import('../features/student/pages/VoicePage').then(module => ({ default: module.VoicePage })));
const ProgressPage = lazy(() => import('../features/student/pages/ProgressPage').then(module => ({ default: module.ProgressPage })));
const PerformancePage = lazy(() => import('../features/student/pages/PerformancePage').then(module => ({ default: module.PerformancePage })));
const AchievementsPage = lazy(() => import('../features/student/pages/AchievementsPage').then(module => ({ default: module.AchievementsPage })));
const SearchPage = lazy(() => import('../features/student/pages/SearchPage').then(module => ({ default: module.SearchPage })));
const NotebookLibraryPage = lazy(() => import('../features/student/pages/NotebookLibraryPage').then(module => ({ default: module.NotebookLibraryPage })));
const NotebookWorkspacePage = lazy(() => import('../features/student/pages/NotebookWorkspacePage').then(module => ({ default: module.NotebookWorkspacePage })));
const TeacherDashboard = lazy(() => import('../features/staff/pages/StaffDashboard').then(module => ({ default: module.TeacherDashboard })));
const AdminDashboard = lazy(() => import('../features/staff/pages/StaffDashboard').then(module => ({ default: module.AdminDashboard })));
const SimpleListPage = lazy(() => import('../features/staff/pages/SimpleListPage').then(module => ({ default: module.SimpleListPage })));
const DetailPage = lazy(() => import('../features/staff/pages/WorkspaceDetailPage').then(module => ({ default: module.WorkspaceDetailPage })));
const CourseManagerPage = lazy(() => import('../features/staff/pages/CourseManagerPage').then(module => ({ default: module.CourseManagerPage })));
const ContentManagementPage = lazy(() => import('../features/staff/pages/ContentManagementPage').then(module => ({ default: module.ContentManagementPage })));
const TeacherStudentsPage = lazy(() => import('../features/staff/pages/ResourcePages').then(module => ({ default: module.TeacherStudentsPage })));
const TeacherAnalyticsPage = lazy(() => import('../features/staff/pages/StaffDashboard').then(module => ({ default: module.TeacherAnalyticsPage })));
const AssessmentStudioPage = lazy(() => import('../features/staff/pages/AssessmentStudioPage').then(module => ({ default: module.AssessmentStudioPage })));
const AdminUserManagement = lazy(() => import('../features/admin/pages/AdminUserManagement').then(module => ({ default: module.AdminUserManagement })));
const AdminAnalyticsPage = lazy(() => import('../features/staff/pages/StaffDashboard').then(module => ({ default: module.AdminAnalyticsPage })));
const AdminActivityPage = lazy(() => import('../features/staff/pages/ResourcePages').then(module => ({ default: module.AdminActivityPage })));
const AdminNotificationsPage = lazy(() => import('../features/staff/pages/ResourcePages').then(module => ({ default: module.AdminNotificationsPage })));
const AdminContentPage = lazy(() => import('../features/staff/pages/ResourcePages').then(module => ({ default: module.AdminContentPage })));
const SettingsPage = lazy(() => import('../features/staff/pages/SettingsPage').then(module => ({ default: module.SettingsPage })));
const CourseDetailPage = lazy(() => import('../features/student/pages/CourseDetailPage').then(module => ({ default: module.CourseDetailPage })));
const ExerciseDetailPage = lazy(() => import('../features/student/pages/ExerciseDetailPage').then(module => ({ default: module.ExerciseDetailPage })));
const CourseCreatePage = lazy(() => import('../features/teacher/pages/CourseCreatePage').then(module => ({ default: module.CourseCreatePage })));
const CourseEditPage = lazy(() => import('../features/teacher/pages/CourseEditPage').then(module => ({ default: module.CourseEditPage })));
const CourseChaptersPage = lazy(() => import('../features/teacher/pages/CourseChaptersPage').then(module => ({ default: module.CourseChaptersPage })));
const CourseVersionsPage = lazy(() => import('../features/teacher/pages/CourseVersionsPage').then(module => ({ default: module.CourseVersionsPage })));
const CourseSchedulePage = lazy(() => import('../features/teacher/pages/CourseSchedulePage').then(module => ({ default: module.CourseSchedulePage })));
const CoursePrerequisitesPage = lazy(() => import('../features/teacher/pages/CoursePrerequisitesPage').then(module => ({ default: module.CoursePrerequisitesPage })));
const CourseExportPage = lazy(() => import('../features/teacher/pages/CourseExportPage').then(module => ({ default: module.CourseExportPage })));
const CourseModerationPage = lazy(() => import('../features/admin/pages/CourseModerationPage').then(module => ({ default: module.CourseModerationPage })));
const QuizAttemptPage = lazy(() => import('../features/student/pages/QuizAttemptPage').then(module => ({ default: module.QuizAttemptPage })));
const QuizResultPage = lazy(() => import('../features/student/pages/QuizResultPage').then(module => ({ default: module.QuizResultPage })));
const QuizOverviewPage = lazy(() => import('../features/student/pages/QuizOverviewPage').then(module => ({ default: module.QuizOverviewPage })));
const QuizLibraryPage = lazy(() => import('../features/student/pages/QuizLibraryPage').then(module => ({ default: module.QuizLibraryPage })));
const ExerciseLibraryPage = lazy(() => import('../features/student/pages/ExerciseLibraryPage').then(module => ({ default: module.ExerciseLibraryPage })));
const ContactPage = lazy(() => import('../features/public/pages/ContactPage').then(module => ({ default: module.ContactPage })));
const FaceAuthPage = lazy(() => import('../features/public/pages/FaceAuthPage').then(module => ({ default: module.FaceAuthPage })));
const FaqPage = lazy(() => import('../features/public/pages/FaqPage').then(module => ({ default: module.FaqPage })));
const ForgotPasswordPage = lazy(() => import('../features/public/pages/ForgotPasswordPage').then(module => ({ default: module.ForgotPasswordPage })));
const UploadMaterialsPage = lazy(() => import('../features/public/pages/UploadMaterialsPage').then(module => ({ default: module.UploadMaterialsPage })));
const ProfilePage = lazy(() => import('../features/student/pages/ProfilePage').then(module => ({ default: module.ProfilePage })));
const SecuritySettingsPage = lazy(() => import('../features/student/pages/SecuritySettingsPage').then(module => ({ default: module.SecuritySettingsPage })));
const EducatorProfilePage = lazy(() => import('../features/educator/pages/EducatorProfilePage').then(module => ({ default: module.EducatorProfilePage })));
const EducatorSecuritySettingsPage = lazy(() => import('../features/educator/pages/EducatorSecuritySettingsPage').then(module => ({ default: module.EducatorSecuritySettingsPage })));

function getRouteRole(backendRole) {
  const map = { etudiant: 'student', professeur: 'teacher', admin: 'admin' };
  return map[backendRole] || 'student';
}

export function RouteBoundary({ children }) {
  const location = useLocation();
  const { user } = useAuth();
  const routeRole = location.pathname.split('/')[1];
  if (['student', 'teacher', 'admin'].includes(routeRole)) {
    if (!user) return <Navigate to={`/auth/login?next=${encodeURIComponent(location.pathname)}`} replace />;
    if (getRouteRole(user.role) !== routeRole) return <Navigate to={`/${getRouteRole(user.role)}/dashboard`} replace />;
  }
  return <>{children}</>;
}

export function RouteOverrides() {
  const path = useLocation().pathname;
  if (path === '/') return <SignatureLanding />;
  if (path === '/student/dashboard') return <AtlasDashboardPage />;
  if (path === '/student/learning-path') return <LearningPathPage />;
  if (path === '/educators') return <EducatorLandingPage />;
  if (path === '/auth/face-login') return <FaceAuthPage />;
  if (path === '/auth/face-capture') return <FaceCapturePage />;
  if (path === '/auth/complete-profile') return <CompleteProfilePage />;
  if (path === '/auth/social-callback') return <SocialCallbackPage />;
  // The email verification link sent by the backend points here (?token=...), and
  // AuthPage.jsx's register flow also sends new users here (no token: "check your inbox").
  if (path === '/auth/verify' || path === '/auth/verify-email') return <EmailVerificationPage />;
  if (path === '/auth/forgot-password' || path === '/auth/reset-password') return <ForgotPasswordPage />;
  if (path === '/contact') return <ContactPage />;
  if (path === '/faq') return <FaqPage />;
  if (path === '/teacher/materials/upload') return <UploadMaterialsPage />;
  return <CompleteApp />;
}

function WorkspaceRouter({ role }) {
  const { pathname } = useLocation();
  if (role === 'student') {
    if (pathname === '/student/notebooks') return <NotebookLibraryPage />;
    if (/^\/student\/notebooks\/[^/]+$/.test(pathname)) return <NotebookWorkspacePage />;
    if (pathname === '/student/search') return <SearchPage />;
    if (pathname === '/student/courses') return <CoursesPage />;
    if (/^\/student\/courses\/[^/]+\/player$/.test(pathname)) return <CourseDetailPage player />;
    if (/^\/student\/courses\/[^/]+$/.test(pathname)) return <CourseDetailPage />;
    if (pathname === '/student/assistant' || /^\/student\/assistant\/[^/]+$/.test(pathname)) return <AssistantPage />;
    if (pathname === '/student/voice-question') return <VoicePage />;
    if (pathname === '/student/progress') return <ProgressPage />;
    if (pathname === '/student/performance') return <PerformancePage />;
    if (pathname === '/student/achievements') return <AchievementsPage />;
    if (/^\/student\/quizzes\/[^/]+\/attempt$/.test(pathname)) return <QuizAttemptPage />;
    if (/^\/student\/quizzes\/[^/]+\/result$/.test(pathname)) return <QuizResultPage />;
    if (pathname === '/student/quizzes') return <QuizLibraryPage />;
    if (/^\/student\/quizzes\/[^/]+$/.test(pathname)) return <QuizOverviewPage />;
    if (/^\/student\/exercises\/[^/]+$/.test(pathname)) return <ExerciseDetailPage />;
    if (pathname === '/student/exercises') return <ExerciseLibraryPage />;
    if (pathname === '/student/profile') return <ProfilePage />;
    if (pathname === '/student/security') return <SecuritySettingsPage />;
    if (!isKnownWorkspacePath(pathname, role)) return <NotFound />;
    return <DetailPage role={role} title={titleFromPath(pathname)} description="Continue building confidence in this learning area." variant={variantFromPath(pathname)} />;
  }
  if (pathname === '/teacher/dashboard') return <TeacherDashboard />;
  if (pathname === '/teacher/courses' || pathname === '/teacher/courses/new' || /^\/teacher\/courses\/[^/]+(?:\/edit)?$/.test(pathname)) return <CourseManagerPage />;
  if (pathname === '/teacher/materials') return <ContentManagementPage />;
  if (pathname === '/teacher/transcriptions') return <ContentManagementPage mode="transcriptions" />;
  if (pathname === '/teacher/summaries') return <ContentManagementPage mode="summaries" />;
  if (['/teacher/audio-processing', '/teacher/pdf-processing'].includes(pathname)) return <ContentManagementPage />;
  if (pathname === '/teacher/students' || /^\/teacher\/students\/[^/]+$/.test(pathname)) return <TeacherStudentsPage />;
  if (pathname === '/teacher/quizzes' || pathname === '/teacher/questions' || pathname === '/teacher/exercises' || pathname === '/teacher/ai-generation') return <AssessmentStudioPage />;
if (pathname === '/teacher/analytics') return <TeacherAnalyticsPage />;
    if (pathname === '/teacher/profile') return <EducatorProfilePage />;
    if (pathname === '/teacher/security') return <EducatorSecuritySettingsPage />;
    if (pathname === '/teacher/settings' || pathname === '/teacher/profile') return <SettingsPage role="teacher" />;
    if (pathname === '/admin/dashboard') return <AdminDashboard />;
  if (pathname === '/admin/users' || pathname === '/admin/students' || pathname === '/admin/teachers') return <AdminUserManagement />;
  if (pathname === '/admin/courses' || pathname === '/admin/quizzes' || pathname === '/admin/exercises') return <AdminContentPage />;
  if (pathname === '/admin/analytics' || pathname === '/admin/ai-usage') return <AdminAnalyticsPage />;
  if (pathname === '/admin/settings' || pathname === '/admin/profile') return <SettingsPage role="admin" />;
  if (pathname === '/admin/activity') return <AdminActivityPage />;
  if (pathname === '/admin/notifications') return <AdminNotificationsPage />;
  if (!isKnownWorkspacePath(pathname, role)) return <NotFound />;
  return <DetailPage role={role} title={titleFromPath(pathname)} description="Manage your Learnwise workspace with clarity." variant={variantFromPath(pathname)} />;
}

function isKnownWorkspacePath(pathname, role) {
  const patterns = role === 'student'
    ? [/^\/student\/(performance|achievements|sessions|activity|notifications|profile|settings)$/]
    : role === 'teacher'
      ? [/^\/teacher\/dashboard$/, /^\/teacher\/courses$/, /^\/teacher\/courses\/new$/, /^\/teacher\/courses\/[^/]+(?:\/edit)?$/, /^\/teacher\/courses\/[^/]+\/chapters$/, /^\/teacher\/courses\/[^/]+\/versions$/, /^\/teacher\/courses\/[^/]+\/schedule$/, /^\/teacher\/courses\/[^/]+\/prerequisites$/, /^\/teacher\/courses\/[^/]+\/export$/, /^\/teacher\/(materials|audio-processing|pdf-processing|transcriptions|summaries|ai-generation|quizzes|questions|exercises|analytics|profile|security|settings)$/, /^\/teacher\/students(?:\/[^/]+)?$/]
      : [/^\/admin\/(dashboard|users|students|teachers|courses|quizzes|exercises|ai-usage|analytics|activity|notifications|settings|profile)$/, /^\/admin\/users\/[^/]+$/];
  return patterns.some(pattern => pattern.test(pathname));
}

export function resolveWorkspaceView(pathname, role = 'student') {
  if (role === 'student') {
    if (pathname === '/student/notebooks') return 'notebook-library';
    if (/^\/student\/notebooks\/[^/]+$/.test(pathname)) return 'notebook-workspace';
    if (pathname === '/student/search') return 'search';
    if (pathname === '/student/courses') return 'courses';
    if (/^\/student\/courses\/[^/]+\/player$/.test(pathname)) return 'course-player';
    if (/^\/student\/courses\/[^/]+$/.test(pathname)) return 'course-detail';
    if (pathname.startsWith('/student/assistant')) return 'assistant';
    if (pathname === '/student/voice-question') return 'voice';
    if (pathname === '/student/progress') return 'progress';
    if (pathname === '/student/performance') return 'performance';
    if (pathname === '/student/achievements') return 'achievements';
    if (/^\/student\/quizzes\/[^/]+\/attempt$/.test(pathname)) return 'quiz-attempt';
    if (/^\/student\/quizzes\/[^/]+\/result$/.test(pathname)) return 'quiz-result';
    if (pathname === '/student/quizzes') return 'quizzes';
    if (/^\/student\/quizzes\/[^/]+$/.test(pathname)) return 'quiz-overview';
    if (/^\/student\/exercises\/[^/]+$/.test(pathname)) return 'exercise-detail';
    if (pathname === '/student/exercises') return 'exercises';
  }
  if (role === 'teacher') {
    if (pathname === '/teacher/ai-generation') return 'teacher-ai-generation';
    if (pathname === '/teacher/analytics') return 'teacher-analytics';
  }
  if (role === 'admin') {
    if (pathname === '/admin/activity') return 'admin-activity';
    if (pathname === '/admin/notifications') return 'admin-notifications';
  }
  if (pathname === `/${role}/dashboard`) return `${role}-dashboard`;
  return 'detail';
}

function titleFromPath(pathname) {
  const value = pathname.split('/').filter(Boolean).at(-1) || 'dashboard';
  return value.replaceAll('-', ' ').replace(/\b\w/g, character => character.toUpperCase());
}

function variantFromPath(pathname) {
  if (pathname.includes('upload') || pathname.includes('processing')) return 'upload';
  if (pathname.includes('edit') || pathname.includes('transcription') || pathname.includes('summary')) return 'editor';
  if (pathname.includes('result') || pathname.includes('activity')) return 'timeline';
  if (pathname.includes('analytics') || pathname.includes('performance') || pathname.includes('usage')) return 'cards';
  if (pathname.includes('attempt')) return 'quiz';
  return pathname.includes('courses') || pathname.includes('users') || pathname.includes('students') ? 'table' : 'cards';
}

export function CompleteApp() {
  const navigate = useNavigate();

  useEffect(() => {
    const handleOnboardingRequired = () => {
      navigate('/auth/complete-profile', { replace: true });
    };

    window.addEventListener('learnwise:onboarding-required', handleOnboardingRequired);

    return () => {
      window.removeEventListener('learnwise:onboarding-required', handleOnboardingRequired);
    };
  }, [navigate]);

  return <Routes>
    <Route path="/" element={<Landing />} />
    <Route path="/about" element={<PublicSectionPage kind="about" title="Learning should feel more human." description="Learnwise combines thoughtful design, multimodal AI, and practical learning science to help more people make progress." />} />
    <Route path="/features" element={<PublicSectionPage kind="features" title="Everything you need to go further." description="From source-grounded notebooks and voice questions to active practice and useful progress signals, your whole journey lives here." />} />
    <Route path="/how-it-works" element={<PublicSectionPage kind="workflow" title="A simple loop for meaningful progress." description="Upload your material, ask better questions, practice deliberately, and use your progress to choose the next step." />} />
    <Route path="/educators" element={<EducatorLandingPage />} />
    <Route path="/terms" element={<LegalPage type="terms" />} />
    <Route path="/privacy" element={<LegalPage type="privacy" />} />
    <Route path="/auth/login" element={<AuthPage />} />
    <Route path="/auth/register" element={<AuthPage register />} />
    <Route path="/student/*" element={<WorkspaceRouter role="student" />} />
    <Route path="/teacher/*" element={<WorkspaceRouter role="teacher" />} />
    <Route path="/teacher/courses/new" element={<CourseCreatePage />} />
    <Route path="/teacher/courses" element={<CourseManagerPage />} />
    <Route path="/teacher/courses/:id/edit" element={<CourseEditPage />} />
    <Route path="/teacher/courses/:id/chapters" element={<CourseChaptersPage />} />
    <Route path="/teacher/courses/:id/versions" element={<CourseVersionsPage />} />
    <Route path="/teacher/courses/:id/schedule" element={<CourseSchedulePage />} />
    <Route path="/teacher/courses/:id/prerequisites" element={<CoursePrerequisitesPage />} />
    <Route path="/teacher/courses/:id/export" element={<CourseExportPage />} />
    <Route path="/admin/*" element={<WorkspaceRouter role="admin" />} />
    <Route path="/403" element={<NotFound />} />
    <Route path="/404" element={<NotFound />} />
    <Route path="/500" element={<NotFound />} />
    <Route path="*" element={<NotFound />} />
  </Routes>;
}
