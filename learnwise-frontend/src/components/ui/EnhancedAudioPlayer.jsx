import React, { useRef, useState, useEffect, useCallback } from 'react';
import { Play, Pause, Volume2, VolumeX, FastForward, Rewind, SkipForward, SkipBack } from 'lucide-react';

export function EnhancedAudioPlayer({
  src,
  transcript = null,
  onTimeUpdate,
  onTranscriptClick,
  className = '',
  autoPlay = false
}) {
  const audioRef = useRef(null);
  const [playing, setPlaying] = useState(autoPlay);
  const [volume, setVolume] = useState(1);
  const [muted, setMuted] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [buffered, setBuffered] = useState(0);
  const [playbackRate, setPlaybackRate] = useState(1);
  const [showTranscript, setShowTranscript] = useState(!!transcript);
  const [activeSegment, setActiveSegment] = useState(-1);
  const [transcriptSegments, setTranscriptSegments] = useState([]);
  const transcriptContainerRef = useRef(null);

  useEffect(() => {
    if (!transcript) return;
    const parsed = typeof transcript === 'string'
      ? transcript.split('\n').filter(Boolean).map((line, i) => ({
          id: i,
          text: line,
          start: i * 15,
          end: (i + 1) * 15
        }))
      : transcript;
    setTranscriptSegments(parsed);
  }, [transcript]);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    const handleTimeUpdate = () => {
      setCurrentTime(audio.currentTime);
      setBuffered(audio.buffered.length ? audio.buffered.end(audio.buffered.length - 1) / audio.duration * 100 : 0);
      onTimeUpdate?.(audio.currentTime);
      if (transcriptSegments.length) {
        const idx = transcriptSegments.findIndex(s => audio.currentTime >= s.start && audio.currentTime < s.end);
        if (idx !== -1 && idx !== activeSegment) {
          setActiveSegment(idx);
          scrollToSegment(idx);
        }
      }
    };
    const handleLoadedMetadata = () => setDuration(audio.duration);
    const handleEnded = () => setPlaying(false);
    const handleProgress = () => setBuffered(audio.buffered.length ? audio.buffered.end(audio.buffered.length - 1) / audio.duration * 100 : 0);
    audio.addEventListener('timeupdate', handleTimeUpdate);
    audio.addEventListener('loadedmetadata', handleLoadedMetadata);
    audio.addEventListener('ended', handleEnded);
    audio.addEventListener('progress', handleProgress);
    return () => {
      audio.removeEventListener('timeupdate', handleTimeUpdate);
      audio.removeEventListener('loadedmetadata', handleLoadedMetadata);
      audio.removeEventListener('ended', handleEnded);
      audio.removeEventListener('progress', handleProgress);
    };
  }, [transcriptSegments, activeSegment, onTimeUpdate]);

  const scrollToSegment = (index) => {
    const container = transcriptContainerRef.current;
    const element = container?.querySelector(`[data-segment="${index}"]`);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  };

  const togglePlay = () => {
    const audio = audioRef.current;
    if (!audio) return;
    if (playing) audio.pause();
    else audio.play();
    setPlaying(!playing);
  };

  const seek = (time) => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.currentTime = Math.max(0, Math.min(time, audio.duration));
  };

  const handleSeek = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const pos = (e.clientX - rect.left) / rect.width;
    const audio = audioRef.current;
    if (audio) seek(pos * audio.duration);
  };

  const changeVolume = (value) => {
    const audio = audioRef.current;
    if (!audio) return;
    const vol = Math.max(0, Math.min(1, value));
    setVolume(vol);
    audio.volume = vol;
    setMuted(vol === 0);
  };

  const toggleMute = () => {
    const audio = audioRef.current;
    if (!audio) return;
    if (muted) {
      audio.volume = volume;
      setMuted(false);
    } else {
      audio.volume = 0;
      setMuted(true);
    }
  };

  const changeRate = (rate) => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.playbackRate = rate;
    setPlaybackRate(rate);
  };

  const skip = (seconds) => {
    const audio = audioRef.current;
    if (!audio) return;
    seek(audio.currentTime + seconds);
  };

  const handleSegmentClick = (segment, index) => {
    seek(segment.start);
    setActiveSegment(index);
    onTranscriptClick?.(segment, index);
  };

  const formatTime = (time) => {
    if (!isFinite(time)) return '0:00';
    const mins = Math.floor(time / 60);
    const secs = Math.floor(time % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (!src) return <div className={`audio-player ${className} empty`}>No audio source</div>;

  return (
    <div className={`audio-player ${className}`}>
      <div className="audio-main-controls">
        <button className="icon-button skip-button" onClick={() => skip(-15)} aria-label="Rewind 15 seconds"><SkipBack size={20} /></button>
        <button className="icon-button play-button" onClick={togglePlay} aria-label={playing ? 'Pause' : 'Play'} aria-pressed={playing}>
          {playing ? <Pause size={28} /> : <Play size={28} />}
        </button>
        <button className="icon-button skip-button" onClick={() => skip(15)} aria-label="Forward 15 seconds"><SkipForward size={20} /></button>
        <div className="progress-wrapper" onClick={handleSeek}>
          <div className="progress-track" role="slider" aria-label="Playback progress" aria-valuemin={0} aria-valuemax={100} aria-valuenow={duration ? (currentTime / duration * 100).toFixed(1) : 0} tabIndex={0}>
            <div className="progress-buffered" style={{ width: `${buffered}%` }} />
            <div className="progress-played" style={{ width: `${duration ? (currentTime / duration * 100) : 0}%` }} />
            <div className="progress-handle" style={{ left: `${duration ? (currentTime / duration * 100) : 0}%` }} />
          </div>
        </div>
        <div className="time-display">
          <span>{formatTime(currentTime)}</span>
          <span>/</span>
          <span>{formatTime(duration)}</span>
        </div>
        <div className="rate-control">
          <select value={playbackRate} onChange={e => changeRate(Number(e.target.value))} aria-label="Playback speed">
            {[0.5, 0.75, 1, 1.25, 1.5, 2].map(r => <option key={r} value={r}>{r}x</option>)}
          </select>
        </div>
        <div className="volume-control">
          <button className="icon-button" onClick={toggleMute} aria-label={muted ? 'Unmute' : 'Mute'} aria-pressed={muted}>
            {muted || volume === 0 ? <VolumeX size={18} /> : <Volume2 size={18} />}
          </button>
          <input type="range" min={0} max={1} step={0.1} value={muted ? 0 : volume} onChange={e => changeVolume(Number(e.target.value))} aria-label="Volume" />
        </div>
      </div>

      {transcriptSegments.length > 0 && (
        <div className="transcript-toggle">
          <button className="secondary-button" onClick={() => setShowTranscript(!showTranscript)}>
            {showTranscript ? 'Hide Transcript' : 'Show Transcript'}
          </button>
        </div>
      )}

      {showTranscript && transcriptSegments.length && (
        <div className="transcript-panel" ref={transcriptContainerRef} role="list" aria-label="Transcript">
          {transcriptSegments.map((segment, index) => (
            <button
              key={segment.id || index}
              data-segment={index}
              className={`transcript-segment ${index === activeSegment ? 'active' : ''}`}
              onClick={() => handleSegmentClick(segment, index)}
              role="listitem"
            >
              <span className="segment-time">{formatTime(segment.start)}</span>
              <span className="segment-text">{segment.text}</span>
            </button>
          ))}
        </div>
      )}
      <audio ref={audioRef} src={src} preload="metadata" />
    </div>
  );
}

export default EnhancedAudioPlayer;