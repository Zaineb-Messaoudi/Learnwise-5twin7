import { useEffect, useState } from 'react';
import { ArrowLeft, ArrowRight, Check, CirclePlay, Play, Sparkles, Loader2, HelpCircle, FileText, Music, BookOpen } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { AppShell } from '../../../layouts/AppShell';
import { Button, PageHeader, ProgressBar } from '../../../components/shared/Primitives';
import { ErrorState, LoadingState } from '../../../components/ui/States';
import { coursesApi } from '../../../api/courses.api';
import { materialsApi } from '../../../api/materials.api';
import { analyticsApi } from '../../../api/analytics.api';
import { quizzesApi } from '../../../api/quizzes.api';
import { isBackendApiEnabled } from '../../../api/client';
import { EngagementTracker } from '../../../components/ui/EngagementTracker';
import { usePresence } from '../../../api/presence.api';
import { PDFViewer } from '../../../components/ui/PDFViewer';
import { EnhancedAudioPlayer } from '../../../components/ui/EnhancedAudioPlayer';
import { LessonNavigator } from '../components/LessonNavigator';
import { VideoPlayer } from '../components/VideoPlayer';
import PropTypes from 'prop-types';
import '../components/courses.css';

const demoCourse = {
  id: 'ai-101',
  title: 'Neural networks basics',
  description: 'Build intuition for how modern models learn from examples.',
  level: 'Intermediate',
  materials_count: 8,
  progress: 68,
};
const demoMaterials = [
  { id: 'chapter-1', title: 'Foundations', status: 'completed', kind: 'document', file: '/media/foundations.pdf' },
  { id: 'chapter-4', title: 'Backpropagation', status: 'completed', kind: 'audio', file: '/media/backpropagation.mp3' },
];
const demoTranscript = '00:00 Welcome to this lesson on neural networks.\n02:18 We begin with the core idea of a prediction compared to an expected result.\n06:42 The error travels backward through each layer, updating the weights.';
const demoSummary = 'Neural networks learn by comparing predictions with expected results. The error is propagated backward through the layers, and the weights are updated to reduce that error over many iterations.';

function recordsFrom(response) {
  return Array.isArray(response) ? response : response?.results || [];
}

function materialUrl(material) {
  return material?.file || material?.file_url || material?.url || material?.src || '';
}

function computeProgress(course, isBackendApiEnabled) {
  return Number(
    course?.progress?.percentage ??
      course?.progress?.completion_percentage ??
      course?.progress ??
      (isBackendApiEnabled ? 0 : 68),
  );
}

async function pollGeneration(generationId, quizzesApi) {
  let generation = await quizzesApi.generation(generationId);
  const attempts = Array.from({ length: 30 }, (_, i) => i);
  await Promise.all(
    attempts.map(async () => {
      if (!generation.status || !['queued', 'processing'].includes(generation.status)) {
        return;
      }
      await new Promise(resolve => setTimeout(resolve, 1500));
      generation = await quizzesApi.generation(generationId);
    }),
  );
  return generation;
}

function fetchContent(
  selected,
  isBackendApiEnabled,
  setTranscript,
  setSummary,
  setContentLoading,
  setContentError,
) {
  if (!selected) {
    setTranscript('');
    setSummary('');
    return;
  }
  if (!isBackendApiEnabled) {
    setTranscript(selected.kind === 'audio' ? demoTranscript : '');
    setSummary(demoSummary);
    return;
  }
  let active = true;
  setContentLoading(true);
  setContentError('');
  const requests = [];
  if (selected.kind === 'audio') {
    requests.push(
      materialsApi.transcription(selected.id)
        .then(result => { if (active) {setTranscript(result.text || '');} })
        .catch(() => { if (active) {setContentError('Could not load the transcript.');} }),
    );
  }
  if (selected.status === 'completed') {
    requests.push(
      materialsApi.summary(selected.id)
        .then(result => { if (active) {setSummary(result.text || '');} })
        .catch(() => { if (active) {setContentError('Could not load the summary.');} }),
    );
  }
  Promise.allSettled(requests).finally(() => { if (active) {setContentLoading(false);} });
  return () => { active = false; };
}

export function CourseDetailPage({ player = false }) {
  const { id = 'ai-101' } = useParams();
  const { totalActive } = usePresence(id);
  const [selectedMaterial, setSelectedMaterial] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [generatingQuiz, setGeneratingQuiz] = useState(false);
  const [quizGenerationError, setQuizGenerationError] = useState('');
  const [quizGenerationSuccess, setQuizGenerationSuccess] = useState('');
  const [transcript, setTranscript] = useState('');
  const [summary, setSummary] = useState('');
  const [contentLoading, setContentLoading] = useState(false);
  const [contentError, setContentError] = useState('');
  const [session, setSession] = useState(null);
  const courseQuery = useQuery({
    queryKey: ['content', 'course', id],
    queryFn: () => coursesApi.detail(id),
    enabled: isBackendApiEnabled,
  });
  const materialsQuery = useQuery({
    queryKey: ['content', 'materials', id],
    queryFn: () => materialsApi.list(id),
    enabled: isBackendApiEnabled,
  });
  const course = isBackendApiEnabled ? courseQuery.data : demoCourse;
  const materials = isBackendApiEnabled ? recordsFrom(materialsQuery.data) : demoMaterials;
  const selected = materials.find(material => material.id === selectedMaterial) || materials.find(material => material.status === 'completed') || materials[0];
  const progress = computeProgress(course, isBackendApiEnabled);

  useEffect(() => {
    fetchContent(selected, isBackendApiEnabled, setTranscript, setSummary, setContentLoading, setContentError);
  }, [selected?.id, selected?.kind, selected?.status, isBackendApiEnabled, setTranscript, setSummary, setContentLoading, setContentError]);

  if (isBackendApiEnabled && (courseQuery.isLoading || materialsQuery.isLoading)) {
    return (
      <AppShell>
        <PageHeader eyebrow="Course workspace" title="Loading course" />
        <LoadingState label="Loading course content" />
      </AppShell>
    );
  }
  if (isBackendApiEnabled && (courseQuery.isError || materialsQuery.isError || !course)) {
    return (
      <AppShell>
        <PageHeader eyebrow="Course workspace" title="This course could not be opened." />
        <ErrorState
          message="Course details or materials are unavailable."
          action={
            <Button
              onClick={() => {
                void courseQuery.refetch();
                void materialsQuery.refetch();
              }}
            >
              Retry
            </Button>
          }
        />
      </AppShell>
    );
  }

  const beginLearning = async () => {
    if (!isBackendApiEnabled) {return;}
    setBusy(true);
    setError('');
    try {
      const nextSession = await analyticsApi.startLearningSession(id);
      setSession(nextSession);
      await analyticsApi.recordActivity({
        session_id: nextSession.id,
        course_id: id,
        activity_type: 'lesson_started',
        material_id: selected?.id,
      });
    } catch {
      setError('Could not start or track this learning session. Retry before continuing.');
    } finally {
      setBusy(false);
    }
  };

  const finishLearning = async () => {
    if (!session?.id) {return;}
    setBusy(true);
    setError('');
    try {
      await analyticsApi.recordActivity({
        session_id: session.id,
        course_id: id,
        activity_type: 'lesson_completed',
        material_id: selected?.id,
      });
      await analyticsApi.finishLearningSession(session.id);
      setSession(null);
    } catch {
      setError('Could not finish this learning session. Your progress event may still be pending; retry to close it.');
    } finally {
      setBusy(false);
    }
  };

  const generatePracticeQuiz = async () => {
    if (!selected) {
      setQuizGenerationError('Select a course material first to generate a quiz from it.');
      return;
    }
    if (!isBackendApiEnabled) {
      setQuizGenerationError('Quiz generation requires backend connection. Enable API mode to use this feature.');
      return;
    }
    setGeneratingQuiz(true);
    setQuizGenerationError('');
    setQuizGenerationSuccess(false);
    try {
      const sourceText = `${selected.title}. ${selected.kind === 'audio' ? 'Audio lecture transcript' : 'Course document content'}. This material covers key concepts for student practice.`;
      const result = await quizzesApi.generate({
        course_id: id,
        source_text: sourceText,
        kind: 'quiz',
        question_count: 5,
        difficulty: 'medium',
      });
      const generationId = result.id;
      if (!generationId) {throw new Error('No generation ID returned');}
      const generation = await pollGeneration(generationId, quizzesApi);
      if (generation.status === 'failed') {throw new Error(generation.error_message || 'Quiz generation failed');}
      const draftQuestions = generation.questions || generation.result?.questions || [];
      if (!draftQuestions.length) {throw new Error('No questions generated');}
      const payload = {
        course_id: id,
        title: `Practice: ${selected.title}`,
        difficulty: 'medium',
        status: 'published',
        questions: draftQuestions.map(q => ({
          prompt: q.prompt || q.text || q.question || '',
          explanation: q.explanation || '',
          choices: (q.choices || q.options || []).map((choice, idx) => ({
            text: typeof choice === 'string' ? choice : choice.text || choice.label || '',
            is_correct: idx === (q.correct_index ?? q.choices?.findIndex(c => c.is_correct) ?? 0),
          })),
        })),
      };
      await quizzesApi.create(payload);
      setQuizGenerationSuccess(true);
      setTimeout(() => setQuizGenerationSuccess(false), 3000);
    } catch (cause) {
      setQuizGenerationError(cause.message || 'Could not generate practice quiz. Please try again.');
    } finally {
      setGeneratingQuiz(false);
    }
  };

  const renderMaterialViewer = () => {
    if (!selected) {return <p className="state-panel">Select a material to begin studying.</p>;}
    if (contentLoading) {return <LoadingState label="Loading material content…" />;}
    const src = materialUrl(selected);
    if (selected.kind === 'audio') {
      return (
        <div className="material-study">
          <div className="study-header">
            <span className="eyebrow"><Music size={14} /> Audio lecture</span>
            <h3>{selected.title || selected.file_name}</h3>
          </div>
          {src ? (
            <EnhancedAudioPlayer src={src} transcript={transcript || null} onTranscriptClick={() => {}} />
          ) : (
            <p className="state-panel">Audio file is not available for this material yet.</p>
          )}
          {summary && (
            <div className="study-summary">
              <span className="eyebrow"><BookOpen size={14} /> AI Summary</span>
              <p>{summary}</p>
            </div>
          )}
        </div>
      );
    }
    if (selected.kind === 'video') {
      return (
        <div className="material-study">
          <div className="study-header">
            <span className="eyebrow"><Play size={14} /> Video lecture</span>
            <h3>{selected.title || selected.file_name}</h3>
          </div>
          {src ? (
            <VideoPlayer src={src} title={selected.title || ''} onTimeUpdate={() => {}} />
          ) : (
            <p className="state-panel">Video file is not available for this material yet.</p>
          )}
        </div>
      );
    }
    return (
      <div className="material-study">
        <div className="study-header">
          <span className="eyebrow"><FileText size={14} /> Course document</span>
          <h3>{selected.title || selected.file_name}</h3>
        </div>
        {src ? (
          <PDFViewer src={src} transcript={transcript || null} summary={summary || null} />
        ) : (
          <p className="state-panel">Document file is not available for this material yet.</p>
        )}
        {summary && (
          <div className="study-summary">
            <span className="eyebrow"><BookOpen size={14} /> AI Summary</span>
            <p>{summary}</p>
          </div>
        )}
      </div>
    );
  };

  return (
    <AppShell>
      <LessonNavigator course={course} selectedMaterial={selected?.id} onMaterialSelect={() => {}} />
      <PageHeader
        eyebrow="Course workspace"
        title={course.title || 'Course'}
        description={course.description || 'Build knowledge through course materials and practice.'}
        action={
          <Link className="button" to={player ? `/student/courses/${id}` : `/student/courses/${id}/player`}>
            {player ? <><ArrowLeft size={15} /> Course overview</> : <><Play size={15} /> Continue lesson</>}
          </Link>
        }
      />
      <section className="chart-card detail-table">
        <span className="eyebrow">{course.level || 'Course'} · {materials.length} materials</span>
        <h2>{player ? selected?.title || 'Your next lesson' : 'A guided path through the fundamentals'}</h2>
        <p className="quiz-helper">{player ? 'Follow the lesson, pause when you need to, and check your understanding before moving on.' : 'Review course materials, then continue with the next available lesson.'}</p>
        <ProgressBar value={progress} /><span>{progress}%</span>
        {error && <p className="upload-error" role="alert">{error}</p>}
        {player ? (
          <>
            <div className="transcript">{materials.map(material => <button type="button" key={material.id} className="course-material-next" onClick={() => setSelectedMaterial(material.id)}><span><strong>{material.title || material.file_name}</strong><small>{material.kind} · {material.status}</small></span>{selected?.id === material.id ? <CirclePlay size={16} /> : <ArrowRight size={16} />}</button>)}</div>
            {contentError && <p className="upload-error" role="alert">{contentError}</p>}
            {renderMaterialViewer()}
            {isBackendApiEnabled && (
              <div className="course-manager-actions">
                {session ? (
                  <Button onClick={() => void finishLearning()} disabled={busy}><Check size={15} />{busy ? 'Saving…' : 'Complete session'}</Button>
                ) : (
                  <Button onClick={() => void beginLearning()} disabled={busy || !selected}><CirclePlay size={15} />{busy ? 'Starting…' : 'Start learning session'}</Button>
                )}
                {session && <output>Learning session active · progress events are being tracked</output>}
              </div>
            )}
          </>
        ) : (
          <>
            <div className="course-materials-list">{materials.map(material => <button type="button" key={material.id} className={`course-material-item ${selected?.id === material.id ? 'selected' : ''}`} onClick={() => setSelectedMaterial(material.id)}><span className="material-icon">{material.kind === 'audio' ? '🎧' : '📄'}</span><span className="material-info"><strong>{material.title || material.file_name}</strong><small>{material.kind} · {material.status}</small></span></button>)}</div>
            {isBackendApiEnabled && (
              <div className="course-student-actions">
                <Button onClick={() => void beginLearning()} disabled={busy || !selected}><CirclePlay size={15} />{busy ? 'Starting…' : 'Start learning session'}</Button>
                <Button variant="secondary" onClick={() => void generatePracticeQuiz()} disabled={generatingQuiz || !selected || !isBackendApiEnabled}><Sparkles size={15} />{generatingQuiz ? <Loader2 size={14} className="spin" /> : 'Generate Practice Quiz'}</Button>
                {quizGenerationError && <p className="quiz-gen-error" role="alert">{quizGenerationError}</p>}
                {quizGenerationSuccess && <p className="quiz-gen-success"><HelpCircle size={14} /> Practice quiz created! Check the Quizzes page.</p>}
                {totalActive > 0 && <span className="total-active">{totalActive} student{totalActive > 1 ? 's' : ''} online</span>}
              </div>
            )}
          </>
        )}
      </section>
      {session && isBackendApiEnabled && !player && (
        <EngagementTracker
          sessionId={session.id}
          onEngagementUpdate={async (sid, engagement) => {
            await analyticsApi.recordActivity({
              session_id: sid,
              activity_type: 'engagement_check',
              engagement_score: engagement.score,
              engagement_present: engagement.present,
              engagement_attentive: engagement.attentive,
              engagement_emotions: engagement.emotions,
              engagement_top_emotion: engagement.topEmotion,
            });
          }}
          interval={30000}
          className="floating-engagement"
        />
      )}
    </AppShell>
  );
}

CourseDetailPage.propTypes = {
  player: PropTypes.bool,
};
