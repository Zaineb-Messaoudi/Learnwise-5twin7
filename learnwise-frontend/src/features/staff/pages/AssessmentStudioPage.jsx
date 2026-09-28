import React, { useEffect, useState } from 'react';
import { AlertCircle, ArrowRight, Check, ChevronDown, LoaderCircle, Plus, Save, Sparkles, Trash2 } from 'lucide-react';
import { AppShell } from '../../../layouts/AppShell';
import { Button, PageHeader } from '../../../components/shared/Primitives';
import { coursesApi } from '../../../api/courses.api';
import { isBackendApiEnabled } from '../../../api/client';
import { quizzesApi } from '../../../api/quizzes.api';
import { exercisesApi } from '../../../api/exercises.api';
import './assessment-studio.css';

const demoQuestions = [
  { prompt: 'What is the main purpose of backpropagation?', choices: ['Update weights using prediction error', 'Store training examples', 'Choose the network architecture automatically', 'Remove the need for validation'], correct_index: 0, explanation: 'Backpropagation calculates gradients used to adjust model weights.' },
  { prompt: 'What does a lower loss usually indicate?', choices: ['The prediction is closer to the expected result', 'The model has more layers', 'The dataset is larger', 'The learning rate is zero'], correct_index: 0, explanation: 'Loss measures the difference between model predictions and target values.' },
  { prompt: 'Why use a validation set?', choices: ['To estimate generalization on unseen examples', 'To train the model twice', 'To replace the training set', 'To remove incorrect labels'], correct_index: 0, explanation: 'Validation helps identify whether a model generalizes beyond its training examples.' },
];

export function AssessmentStudioPage() {
  const [courses, setCourses] = useState(isBackendApiEnabled ? [] : [{ id: 'neural-networks', title: 'AI & Machine Learning' }]);
  const [courseId, setCourseId] = useState(isBackendApiEnabled ? '' : 'neural-networks');
  const [topic, setTopic] = useState('Neural networks · Chapter 4');
  const [kind, setKind] = useState('quiz');
  const [difficulty, setDifficulty] = useState('medium');
  const [questionCount, setQuestionCount] = useState(3);
  const [questions, setQuestions] = useState([]);
  const [generationId, setGenerationId] = useState(null);
  const [quizId, setQuizId] = useState(null);
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!isBackendApiEnabled) return undefined;
    let active = true;
    coursesApi.list().then(response => {
      if (!active) return;
      const items = Array.isArray(response) ? response : response.results || [];
      setCourses(items);
      setCourseId(items[0]?.id || '');
    }).catch(() => { if (active) setError('Could not load courses. Refresh the page and try again.'); });
    return () => { active = false; };
  }, []);

  const generate = async event => {
    event.preventDefault();
    if (!courseId || !topic.trim()) {
      setError('Choose a course and enter a topic to generate from.');
      return;
    }
    setBusy(true);
    setError('');
    setNotice('');
    setStatus('processing');
    setQuestions([]);
    try {
      if (!isBackendApiEnabled) {
        await new Promise(resolve => window.setTimeout(resolve, 500));
        setQuestions(Array.from({ length: Number(questionCount) }, (_, index) => demoQuestions[index % demoQuestions.length]));
        setStatus('review');
        setNotice('Example questions created. Review and edit before publishing; no AI service was called.');
        return;
      }
      let result = await quizzesApi.generate({
        course_id: courseId,
        source_text: topic.trim(),
        kind,
        question_count: Number(questionCount),
        difficulty,
      });
      if (result.id) setGenerationId(result.id);
      for (let attempt = 0; result.status && ['queued', 'processing'].includes(result.status) && result.id && attempt < 30; attempt += 1) {
        await new Promise(resolve => window.setTimeout(resolve, 1500));
        result = await quizzesApi.generation(result.id);
      }
      if (result.status === 'failed') throw new Error(result.error_message || 'Generation failed. Edit the source and try again.');
      const draft = result.questions || result.result?.questions || [];
      if (!draft.length) throw new Error('Generation finished without questions. Retry with a clearer course topic.');
      setQuestions(draft.map(question => ({
        prompt: question.prompt || question.text || question.question || '',
        choices: (question.choices || question.options || []).map(choice => typeof choice === 'string' ? choice : choice.text),
        correct_index: question.correct_index ?? question.choices?.findIndex(choice => choice.is_correct) ?? 0,
        explanation: question.explanation || '',
      })));
      setStatus('review');
      setNotice('Draft generated. Review every question and correct answer before saving or publishing.');
    } catch (cause) {
      setStatus('failed');
      setError(cause instanceof Error ? cause.message : 'Could not generate this assessment. Check your connection and retry.');
    } finally { setBusy(false); }
  };

  const updateQuestion = (index, changes) => setQuestions(current => current.map((question, itemIndex) => itemIndex === index ? { ...question, ...changes } : question));
  const updateChoice = (questionIndex, choiceIndex, value) => setQuestions(current => current.map((question, itemIndex) => itemIndex === questionIndex ? { ...question, choices: question.choices.map((choice, optionIndex) => optionIndex === choiceIndex ? value : choice) } : question));
  const addQuestion = () => setQuestions(current => [...current, { prompt: '', choices: ['', '', '', ''], correct_index: 0, explanation: '' }]);
  const saveDraft = async publish => {
    if (!questions.length || questions.some(question => !question.prompt.trim() || question.choices.length < 2 || question.choices.some(choice => !choice.trim()))) {
      setError('Complete each question and at least two choices before saving.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      if (isBackendApiEnabled) {
        const payload = { course_id: courseId, title: topic.trim(), difficulty, status: 'draft', questions: questions.map(question => ({ prompt: question.prompt, explanation: question.explanation, choices: question.choices.map((text, index) => ({ text, is_correct: index === Number(question.correct_index) })) })) };
        const saved = kind === 'quiz'
          ? quizId ? await quizzesApi.update(quizId, payload) : await quizzesApi.create(payload)
          : quizId ? await exercisesApi.update(quizId, payload) : await exercisesApi.create(payload);
        const savedId = saved.id || quizId;
        setQuizId(savedId);
        if (publish && savedId) {
          if (kind === 'quiz') await quizzesApi.publish(savedId);
          else await exercisesApi.publish(savedId);
        }
      }
      setStatus(publish ? 'published' : 'saved');
      setNotice(publish ? 'Assessment updated.' : 'Draft updated.');
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not save the assessment. Your edits are still on this page.');
    } finally { setBusy(false); }
  };

  return <AppShell role="teacher"><PageHeader eyebrow="Assessment · Teacher workspace" title="Generate, review, teach." description="Create a draft from a course topic, check every answer, then publish it for your learners." />
    <div className="assessment-studio">
      <form className="assessment-generator" onSubmit={generate}>
        <div className="assessment-generator-heading"><span className="assessment-spark"><Sparkles size={19}/></span><div><span className="eyebrow">AI DRAFT BUILDER</span><h2>Start with a learning goal</h2></div></div>
        <label>Course<select value={courseId} onChange={event => setCourseId(event.target.value)} disabled={busy}><option value="">Choose a course</option>{courses.map(course => <option key={course.id} value={course.id}>{course.title}</option>)}</select></label>
        <label>Topic or source focus<input name="source_text" value={topic} onChange={event => setTopic(event.target.value)} placeholder="e.g. Backpropagation · Chapter 4…" /></label>
        <div className="assessment-fields">
          <label>Assessment type<select value={kind} onChange={event => setKind(event.target.value)}><option value="quiz">Quiz</option><option value="exercise">Exercise set</option></select></label>
          <label>Difficulty<select value={difficulty} onChange={event => setDifficulty(event.target.value)}><option value="easy">Foundational</option><option value="medium">On-level</option><option value="hard">Stretch</option></select></label>
          <label>Questions<select value={questionCount} onChange={event => setQuestionCount(event.target.value)}>{[3, 5, 8, 10].map(count => <option key={count} value={count}>{count}</option>)}</select></label>
        </div>
        {!isBackendApiEnabled && <p className="assessment-demo-note">These editable sample questions are not generated by an AI service.</p>}
        <Button type="submit" disabled={busy || !courseId}><Sparkles size={15}/>{busy ? 'Generating…' : `Generate ${kind === 'quiz' ? 'quiz' : 'exercises'}`}<ArrowRight size={15}/></Button>
        {error && <p className="assessment-error" role="alert"><AlertCircle size={15}/>{error}</p>}
        {notice && <p className="assessment-notice" role="status"><Check size={15}/>{notice}</p>}
        {status === 'processing' && <p className="assessment-status"><LoaderCircle size={15}/> Preparing a reviewable draft…</p>}
      </form>
      <section className="assessment-review" aria-labelledby="assessment-review-heading">
        <header><div><span className="eyebrow">TEACHER REVIEW REQUIRED</span><h2 id="assessment-review-heading">{questions.length ? `${questions.length} draft questions` : 'Your draft will appear here'}</h2></div>{questions.length > 0 && <span className={`assessment-state ${status}`}>{status === 'published' ? 'Published' : status === 'saved' ? 'Draft saved' : 'Needs review'}</span>}</header>
        {!questions.length ? <div className="assessment-empty"><Sparkles size={25}/><p>Choose a course and learning goal to create an editable assessment draft.</p></div> : <div className="assessment-question-list">{questions.map((question, index) => <article className="assessment-question" key={`${generationId || 'demo'}-${index}`}><div className="assessment-question-head"><span>QUESTION {String(index + 1).padStart(2, '0')}</span><button type="button" aria-label={`Remove question ${index + 1}`} onClick={() => setQuestions(current => current.filter((_, itemIndex) => itemIndex !== index))}><Trash2 size={15}/></button></div><label>Question<textarea rows={2} value={question.prompt} onChange={event => updateQuestion(index, { prompt: event.target.value })} /></label><fieldset><legend>Answer choices <span>Select the correct answer</span></legend>{question.choices.map((choice, choiceIndex) => <label className="assessment-choice" key={`${index}-${choiceIndex}`}><input type="radio" name={`correct-${index}`} checked={Number(question.correct_index) === choiceIndex} onChange={() => updateQuestion(index, { correct_index: choiceIndex })}/><input value={choice} onChange={event => updateChoice(index, choiceIndex, event.target.value)} aria-label={`Question ${index + 1} choice ${choiceIndex + 1}`} placeholder={`Choice ${choiceIndex + 1}`}/></label>)}</fieldset><label>Explanation<input value={question.explanation || ''} onChange={event => updateQuestion(index, { explanation: event.target.value })} placeholder="Why is this the correct answer?"/></label></article>)}</div>}
        {questions.length > 0 && <footer className="assessment-review-actions"><button type="button" className="assessment-add-question" onClick={addQuestion}><Plus size={15}/> Add question <ChevronDown size={14}/></button><div><Button variant="secondary" disabled={busy} onClick={() => void saveDraft(false)}><Save size={14}/> Save draft</Button><Button disabled={busy} onClick={() => void saveDraft(true)}><Check size={14}/>{busy ? 'Saving…' : 'Publish'}</Button></div></footer>}
      </section>
    </div>
  </AppShell>;
}
