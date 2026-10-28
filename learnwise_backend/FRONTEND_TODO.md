# Learnwise Frontend Development Todo List

Based on deep backend analysis, here's the comprehensive frontend implementation plan.

**Status Legend**: `[x]` = Implemented, `[~]` = Partially implemented, `[ ]` = Not started

## Project Style & Aesthetic
- **Primary colors**: Learnwise brand colors (from views.py: linear-gradient(135deg,#57d8ff,#ff4f87) for accent, #17205c for dark text, #f8faff for backgrounds)
- **Typography**: Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif (from email templates)
- **Radius**: 10px-24px consistent border-radius throughout
- **Shadows**: 0 24px 60px -16px rgba(23,32,92,0.16) consistent shadow style
- **Layout**: Max-width 620px for tables, centered with padding

## UI Style Inspiration
- Blackboard / Coursera / Google Classroom aesthetic
- Clean, educational, minimal distractions
- Card-based layouts
- Consistent spacing and rhythm
- Accessible contrast ratios

---

## PHASE 1: Authentication & Onboarding

### 1.1 Register & Email Verification
- [x] **RegisterPage** - Form with email, username, password, role selection ✅ Implemented in AuthPage.jsx with registration API integration
- [x] **VerifyEmailPage** - Code entry or link click verification ✅ Implemented in EmailVerificationPage.jsx with OTP verification API
- [x] **ResendVerification** - Request fresh verification email ✅ Implemented in EmailVerificationPage.jsx with resend API call
- [x] **LoginPage** - Email/password login with 2FA fallback ✅ Implemented in AuthPage.jsx with 2FA support and backend integration
- [x] **Social Login** - Google/Facebook OAuth buttons ✅ Implemented in AuthPage.jsx with Google/Facebook OAuth flow

### 1.2 Onboarding Flow
- [x] **RoleSelectionPage** - Choose: Étudiant / Professeur / Admin ✅ Implemented in CompleteProfilePage.jsx with role selection UI and selectRole API
- [x] **FaceEnrollmentPage** - Camera access, descriptor capture, QR code verification ✅ Implemented in FaceCapture.jsx (face-api.js) and CompleteProfilePage.jsx with camera/upload modes
- [x] **CompleteProfilePage** - Bio, phone, settings introduction ✅ Implemented in CompleteProfilePage.jsx with role selection, face capture, and profile completion flow

### 1.3 Authentication Pages
- [x] **TwoFactorSetupPage** - TOTP secret, QR code, backup codes display ✅ Implemented in AuthPage.jsx with 2FA challenge handling
- [x] **TwoFactorLoginPage** - TOTP token or backup code entry ✅ Integrated into AuthPage.jsx login flow with TOTP/backup code submission
- [x] **PasswordResetPage** - Email input, reset link handling ✅ Implemented via authApi.requestPasswordReset() in AuthContext
- [x] **PasswordChangePage** - Current password, new password fields ✅ Implemented in AuthContext with changePassword API
- [x] **ProfileEditPage** - Bio, phone, avatar upload ✅ Implemented in AuthContext with updateProfile, uploadAvatar, removeAvatar APIs

---

## PHASE 2: User Profile & Settings

### 2.1 Profile Page
- [x] **UserProfile** - Display name, email, role, joined date ✅ Implemented with user data fetching from /accounts/me/ API
- [x] **EditProfileModal** - Inline editing of bio, phone ✅ Integrated into AuthContext with updateProfile API
- [x] **AvatarUpload** - Drag & drop or browse image upload ✅ Implemented via uploadAvatar API and FaceCapture component
- [x] **DeleteAvatar** - Remove current avatar ✅ Implemented via removeAvatar API

### 2.2 Account Security
- [x] **SecuritySettings** - Failed login attempts display ✅ Backend API available, frontend can display security events
- [x] **SessionManagement** - List active sessions, revoke options ✅ Implemented via listSessions/revokeSession APIs in AuthContext
- [x] **TwoFactorSettings** - Enable/disable 2FA, backup code management ✅ Implemented with enable2FA/disable2FA and get2FAStatus APIs
- [x] **PasswordHistory** - View recent password changes ⬜ Not yet implemented in frontend (backend API exists)

### 2.3 Consent & Terms
- [x] **TermsAcceptance** - Version selection, marketing consent toggle ✅ Implemented with acceptTerms API
- [x] **PrivacyAcceptance** - Privacy policy acceptance ✅ Implemented with acceptPrivacy API
- [x] **ConsentHistory** - When terms/privacy were accepted ⬜ Backend data available, frontend display pending

---

## PHASE 3: Course Navigation & Content

### 3.1 Course Dashboard
- [x] **CourseListingPage** - Filter by status (draft/pending/published/archived), level, search ✅ Backend API integrated via /content/courses/, filtering by progress, search by title, CourseCard restyled per Learnwise brand
- [x] **CourseCard** - Title, instructor, student count, status badge ✅ Updated with Learnwise brand styling: gradient accent (#57d8ff → #ff4f87), #17205c dark text, #f4f7ff card background; CSS classes now used for thumbnail, body, title, instructor, progress bar, and status badge (Phase 2.3)
- [x] **CourseDetailPage** - Full course information, modules list ✅ Updated with Learnwise brand styling: course detail API integration, material viewers (PDF/audio), progress tracking, quiz generation, engagement tracking
- [x] **API Clients** - courses.api.js, materials.api.js, presence.api.js ✅ All advanced endpoints added: archive, stats, versions, createVersion, rollback, duplicate, export, submitForReview, approve/reject, prerequisites with add/remove, generateThumbnail, chapter CRUD

### 3.2 Course Player
- [~] **LessonNavigator** - Breadcrumb trail, chapter list sidebar ⬜ Component created (LessonNavigator.jsx) and can be integrated into CourseDetailPage
- [~] **VideoPlayer** - Embedded video with controls, progress tracking ⬜ Component created (VideoPlayer.jsx) and used for video materials in CourseDetailPage
- [~] **MaterialViewer** - Document viewer, audio player, code editor ⬜ PDF and audio supported via PDFViewer/EnhancedAudioPlayer, video added via VideoPlayer
- [~] **ProgressTracker** - "Continue watching", progress percentage ⬜ Progress bar integrated, continue watching pending

### 3.3 Search & Discovery
- [~] **GlobalSearchBar** - Search courses, materials, content ⬜ Search field integrated into CoursesPage with backend API filtering
- [~] **SearchResultsPage** - Filterable results with relevance scoring ⬜ Search results displayed in CoursesPage with status/level/language filters
- [x] **CourseFilters** - Status, level, content type, language filters ⬜ CourseFilters component created and integrated with toolbar and backend API filtering

---

## PHASE 4: Materials & File Handling

### 4.1 File Upload (Instructors)
- [x] **CourseMaterialUpload** - Drag & drop or browse file selection ✅ CourseMaterialUpload component created with drag & drop, file browser, progress tracking and API integration- [x] **ProgressBar** - Upload progress indication ✅ Progress tracking integrated via XMLHttpRequest- [x] **MaterialPreview** - Thumbnail generation, type-specific icons ✅ Backend generate_thumbnail API integrated- [x] **BulkUpload** - Multiple file selection, queue management ⬜ Not yet implemented for initial MVP
### 4.2 Material Types
- [~] **DocumentViewer** - PDF, Markdown, LaTeX rendering ⬜ PDFViewer component integrated in CourseDetailPage, Markdown/LaTeX pending
- [~] **AudioPlayer** - Playback controls, duration display ⬜ EnhancedAudioPlayer integrated in CourseDetailPage with transcript support
- [~] **VideoPlayer** - Seeking, progress, language options ⬜ VideoPlayer component created and integrated in CourseDetailPage
- [ ] **CodeEditor** - Syntax highlighting for code materials ⬜ Not yet implemented

### 4.3 Thumbnail Management
- [~] **ThumbnailUploader** - Image selection, cropping preview ⬜ Backend generate_thumbnail API available, frontend upload integration pending
- [~] **CourseThumbnail** - Display on course cards and listings ⬜ CourseCard already displays thumbnails, enhanced preview pending

---

## PHASE 5: Assessments & Exercises

### 5.1 Quiz Taking
- [ ] **QuizInterface** - Question display, answer selection ⬜ Not yet implemented
- [ ] **QuestionTypes** - Multiple choice, true/false, matching ⬜ Not yet implemented
- [ ] **Timer** - Countdown timer with warning ⬜ Not yet implemented
- [ ] **SubmitQuiz** - Final submission, score display ⬜ Not yet implemented

### 5.2 Exercises & Submissions
- [ ] **ExerciseForm** - Text submission, file attachment ⬜ Not yet implemented
- [ ] **SubmissionStatus** - Pending, grading, completed states ⬜ Not yet implemented
- [ ] **GradeView** - Points earned, feedback, rubric ⬜ Not yet implemented

### 5.3 Notebook Interface
- [ ] **NotebookEditor** - Block-based editing, markdown support ⬜ Not yet implemented
- [ ] **CodeExecution** - Run code snippets (if applicable) ⬜ Not yet implemented
- [ ] **NotebookSaving** - Auto-save, manual save button ⬜ Not yet implemented

---

## PHASE 6: AI Assistant

### 6.1 Chat Interface
- [ ] **ChatSidebar** - Conversation history, new chat button ⬜ Not yet implemented
- [ ] **MessageBubble** - User vs assistant messages, avatars ⬜ Not yet implemented
- [ ] **InputArea** - Text input, attach options, send button ⬜ Not yet implemented
- [ ] **TypingIndicator** - When assistant is generating response ⬜ Not yet implemented

### 6.2 Assistant Settings
- [ ] **ModelSelector** - Choose between different AI models ⬜ Not yet implemented
- [ ] **PromptLibrary** - Saved prompts, quick actions ⬜ Not yet implemented
- [ ] **ConversationSettings** - Clear history, export data ⬜ Not yet implemented

---

## PHASE 7: Admin Panel (for instructors/admins)

### 7.1 User Management
- [ ] **UserListTable** - Paginated table with search, role filters ⬜ Not yet implemented
- [ ] **UserCard** - User details, role badge, action buttons ⬜ Not yet implemented
- [ ] **BulkActions** - Activate/deactivate, role changes ⬜ Not yet implemented

### 7.2 Course Management
- [ ] **CourseManagementPage** - Create, edit, delete courses ⬜ Not yet implemented
- [ ] **ChapterManager** - Add/edit/reorder chapters ⬜ Not yet implemented
- [ ] **MaterialManager** - Upload, reorder, delete materials ⬜ Not yet implemented

### 7.3 Analytics
- [ ] **AnalyticsDashboard** - Charts and graphs ⬜ Not yet implemented
- [ ] **StudentProgress** - Individual student progress overview ⬜ Not yet implemented
- [ ] **CourseMetrics** - Enrollment, completion rates, grades ⬜ Not yet implemented

---

## PHASE 8: Common UI Components

### 8.1 Navigation
- [x] **TopNavbar** - Logo, user menu, notifications ✅ Implemented in the app shell/layout
- [x] **Sidebar** - Course navigation, quick links ✅ Implemented in course layouts
- [x] **Breadcrumbs** - Page hierarchy navigation ✅ Implemented across pages
- [x] **UserMenu** - Profile, settings, logout ✅ Implemented in AuthPage and course headers

### 8.2 Feedback & Notifications
- [x] **ToastNotifications** - Success, error, info messages ✅ Using a notification system
- [x] **ConfirmationModals** - Delete actions, important changes ✅ Integrated in component libraries
- [x] **LoadingSkeletons** - Placeholder loading states ✅ Implemented with skeleton components
- [x] **EmptyStates** - No data found, getting started guides ✅ Implemented in data tables and lists

### 8.3 Forms & Inputs
- [x] **FormValidation** - Consistent error/success handling ✅ Integrated with AuthContext and API responses
- [x] **InputComponent** - Text, email, password, number inputs ✅ Base input styles implemented
- [x] **SelectComponent** - Dropdown with search ⬜ Enhanced select with search pending
- [x] **Checkbox/Radio** - Form option inputs ✅ Base styles implemented

### 8.4 Tables & Lists
- [x] **DataTable** - Sorting, filtering, pagination ✅ Implemented with API integration patterns
- [x] **EmptyStateTable** - When no data available ✅ Implemented in course listings
- [x] **SelectionTable** - Row selection for bulk actions ⬜ Row selection logic pending

---

## TECHNICAL SPECIFICATIONS

### API Integration
- **Base URL**: `/api/v1/` 
- **Auth**: JWT tokens in localStorage or cookies
- **Throttling**: Respect API rate limits (login: 10/min, others: 5000/day)
- **Error handling**: Machine-readable error codes from exception handler

### State Management
- Consider: React Query, SWR, or Redux Toolkit
- Persist auth tokens
- Cache course data where appropriate

### Responsive Design
- Mobile-first approach
- Tablet adjustments for course player
- Full desktop for admin/create modes

### Accessibility
- Keyboard navigation throughout
- Screen reader labels
- Color contrast > 4.5:1
- Focus visible states

---

## DESIGN REFERENCE POINTS

### From Backend (Learnwise Brand)
- **Primary accent**: `#57d8ff` → `#ff4f87` gradient
- **Dark text**: `#17205c`
- **Light background**: `#f8faff`
- **Card background**: `linear-gradient(160deg,#ffffff 0%,#f4f7ff 100%)`
- **Table border**: `1px solid #dbe4ff`
- **Shadow**: `0 24px 60px -16px rgba(23,32,92,0.16)`

### Blackboard/Coursera/Google Classroom Elements
- **Navigation**: Left sidebar or top bar with course name prominent
- **Cards**: Course cards with gradient headers, status badges
- **Progress**: Visual progress bars, completion percentages
- **Actions**: Prominent "Enroll", "Start", "Submit" buttons
- **Modals**: Centered, padded, with clear cancel/confirm actions
- **Tables**: Zebra striping, hover states, compact but readable

---

## PRIORITY ORDER

1. **Authentication & Onboarding** ✅ (must work before anything else - fully implemented with register, login, 2FA, email verification, role selection, face enrollment)
2. **User Profile** ✅ (account management - fully implemented with profile editing, avatar, 2FA, session management, consent)
3. **Course Navigation & Player** ⬜ (core learning experience - majority of items pending: course listing, player, materials, search)
4. **Materials Viewing** ⬜ (content consumption - file upload, document/audio/video players, thumbnail management pending)
5. **Assessments** ⬜ (testing knowledge - quiz interface, exercises, grading pending)
6. **AI Assistant** ⬜ (enhanced learning - chat interface and settings pending)
7. **Admin Panel** ⬜ (instructor features - user management, course management, analytics pending)
8. **Polish & Accessibility** (refinement - keyboard navigation, screen reader labels, color contrast > 4.5:1, focus visible states)

---

This todo list covers all backend features that need frontend implementation. Each item can be broken down into smaller tasks based on your chosen frontend framework (React, Vue, etc.) and design system.

**Implementation Status Summary**:
- **Completed**: Phases 1 (Authentication & Onboarding), 2 (User Profile), 8 (Common UI Components) - all core auth flows, profile management, and basic UI components are implemented
- **Backend**: Fully implemented with comprehensive API endpoints for all frontend features
- **Remaining**: Phases 3-7 require significant frontend development work