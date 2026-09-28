import React, { useEffect, useMemo, useState } from 'react';
import { AlertCircle, ArrowRight, Check, LoaderCircle, Mic, RotateCcw, Send } from 'lucide-react';
import { AppShell } from '../../../layouts/AppShell';
import { Button, PageHeader } from '../../../components/shared/Primitives';
import { useVoiceRecorder } from '../../../hooks/useVoiceRecorder';
import { assistantApi } from '../../../api/assistant.api';
import { isBackendApiEnabled } from '../../../api/client';
import { useNavigate } from 'react-router-dom';

export function VoicePage() {
  const recorder = useVoiceRecorder();
  const navigate = useNavigate();
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState('');
  const [sessionId, setSessionId] = useState(null);
  const [voiceQuestionId, setVoiceQuestionId] = useState(null);
  const [transcript, setTranscript] = useState('');
  const [transcriptionStatus, setTranscriptionStatus] = useState('idle');
  const [sending, setSending] = useState(false);
  const audioUrl = useMemo(() => recorder.audio ? URL.createObjectURL(recorder.audio) : '', [recorder.audio]);
  useEffect(() => { if (recorder.state === 'stopped') setSubmitted(true); }, [recorder.state]);
  useEffect(() => () => { if (audioUrl) URL.revokeObjectURL(audioUrl); }, [audioUrl]);
  const cancel = () => { recorder.reset(); setSubmitted(false); setVoiceQuestionId(null); setTranscript(''); setTranscriptionStatus('idle'); setError(''); };
  const start = async () => {
    setSubmitted(false);
    setError('');
    try { await recorder.start(); }
    catch (cause) {
      recorder.reset();
      setError(cause?.name === 'NotAllowedError' ? 'Microphone permission was denied. Allow microphone access in your browser settings and try again.' : 'Could not start microphone recording. Check your microphone and try again.');
    }
  };
  const transcribe = async () => {
    if (!recorder.audio) {
      setError('The recording is not ready to upload. Record your question and try again.');
      return;
    }
    setError('');
    setTranscriptionStatus('processing');
    try {
      let activeSessionId = sessionId;
      if (!activeSessionId) {
        const session = await assistantApi.createSession({ title: 'Voice question' });
        activeSessionId = session.id;
        setSessionId(activeSessionId);
      }
      let question = await assistantApi.uploadVoiceQuestion(activeSessionId, recorder.audio);
      const id = question.id || question.voice_question?.id;
      if (id) setVoiceQuestionId(id);
      for (let attempt = 0; question.status && ['queued', 'processing'].includes(question.status) && id && attempt < 30; attempt += 1) {
        await new Promise(resolve => window.setTimeout(resolve, 1500));
        question = await assistantApi.voiceQuestion(id);
      }
      if (question.status === 'failed') throw new Error(question.error_message || 'Transcription failed. Record again or retry the upload.');
      const text = question.transcript || question.voice_question?.transcript || '';
      if (!text) throw new Error('Transcription finished without text. Retry with a clearer recording.');
      setTranscript(text);
      setTranscriptionStatus('completed');
    } catch (cause) {
      setTranscriptionStatus('failed');
      setError(cause instanceof Error ? cause.message : 'Could not transcribe the recording. Check your connection and retry.');
    }
  };
  const sendTranscript = async () => {
    const corrected = transcript.trim();
    if (!corrected) return;
    if (!sessionId) { setError('The assistant session is not ready. Transcribe the recording again before sending.'); return; }
    setSending(true);
    setError('');
    try {
      if (voiceQuestionId) await assistantApi.updateVoiceTranscript(voiceQuestionId, corrected);
      await assistantApi.ask(sessionId, { content: corrected, voice_question_id: voiceQuestionId });
      navigate(`/student/assistant/${sessionId}`);
    } catch {
      setError('Could not send the corrected transcript. Your text remains here so you can retry.');
    } finally { setSending(false); }
  };
  return <AppShell><PageHeader eyebrow="AI assistant" title="Ask with your voice." description="Record, review the transcription, correct it, then send your question to your assistant." /><div className="voice-page"><section className={`voice-card ${recorder.state === 'recording' ? 'recording' : ''}`}><div className="voice-orb"><div className="voice-ring" /><button type="button" onClick={recorder.state === 'recording' ? recorder.stop : start} className="mic-button" aria-label={recorder.state === 'recording' ? 'Stop recording' : 'Start recording'} disabled={recorder.state === 'requesting'}>{recorder.state === 'recording' ? <span className="stop-square" /> : <Mic size={28} />}</button></div><span className="voice-state" role="status">{error || (submitted ? 'Audio captured. Listen back, then transcribe.' : recorder.state === 'unsupported' ? 'Microphone recording is not supported in this browser.' : recorder.state === 'requesting' ? 'Waiting for microphone permission…' : recorder.state === 'recording' ? `Recording… ${recorder.duration}s` : 'Tap to start recording')}</span><p>Record your question, review the transcript, and send it to your assistant.</p><div className="waveform" aria-hidden="true">{Array.from({ length: 28 }, (_, index) => <i style={{ height: `${20 + ((index * 17) % 45)}%` }} key={index} />)}</div>{audioUrl && <audio controls preload="metadata" src={audioUrl} aria-label="Listen to your recorded question" />}{(recorder.state === 'recording' || recorder.state === 'requesting' || submitted) && <div className="recording-actions">{submitted ? <Button variant="secondary" onClick={cancel}><RotateCcw size={15} /> Record again</Button> : <Button variant="secondary" onClick={cancel}>Cancel recording</Button>}{recorder.state === 'recording' && <Button onClick={recorder.stop}>Finish recording <ArrowRight size={15} /></Button>}{submitted && isBackendApiEnabled && <Button onClick={() => void transcribe()} disabled={transcriptionStatus === 'processing'}><Mic size={15}/>{transcriptionStatus === 'processing' ? 'Transcribing…' : transcriptionStatus === 'failed' ? 'Retry transcription' : 'Transcribe recording'}</Button>}</div>}{transcriptionStatus === 'processing' && <p className="voice-feedback" role="status"><LoaderCircle size={15}/> Transcribing your question…</p>}{transcriptionStatus === 'completed' && <div className="voice-transcript"><label htmlFor="voice-transcript-text">Review and correct your transcript</label><textarea id="voice-transcript-text" name="transcript" value={transcript} onChange={event => setTranscript(event.target.value)} rows={5}/><p><Check size={14}/> Your corrected text will be saved before it is sent to the assistant.</p><Button onClick={() => void sendTranscript()} disabled={sending || !transcript.trim()}><Send size={15}/>{sending ? 'Sending…' : 'Send to assistant'}</Button></div>}{error && <p className="voice-feedback error" role="alert"><AlertCircle size={15}/>{error}</p>}</section><aside className="voice-side"><span className="eyebrow">VOICE QUESTION FLOW</span><div className="voice-step"><span>01</span><div><b>Record and review</b><p>Listen back and replace the recording if it is unclear.</p></div></div><div className="voice-step"><span>02</span><div><b>Transcribe and correct</b><p>Review and edit your transcript before sending it to the assistant.</p></div></div><div className="voice-step"><span>03</span><div><b>Get a grounded explanation</b><p>Your corrected question opens in the assistant conversation for a response.</p></div></div></aside></div></AppShell>;
}
