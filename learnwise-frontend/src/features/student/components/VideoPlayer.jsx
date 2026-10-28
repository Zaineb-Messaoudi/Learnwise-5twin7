import React, { useRef, useState, useCallback } from 'react';
import { Play, Pause, Loader2, FastForward, Rewind, SkipForward, SkipBack } from 'lucide-react';

export function VideoPlayer({ src, title, onTimeUpdate, className = '', autoPlay = false, width = '100%', height = '400px' }) {
  const videoRef = useRef(null);
  const [playing, setPlaying] = useState(autoPlay);
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [buffered, setBuffered] = useState(0);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handleTimeUpdate = () => {
      setCurrentTime(video.currentTime);
      const bufferedEnd = video.buffered.length ? video.buffered.end(video.buffered.length - 1) / video.duration * 100 : 0;
      setBuffered(bufferedEnd);
      onTimeUpdate?.(video.currentTime);
    };

    const handleLoadedMetadata = () => setDuration(video.duration);

    const handleEnded = () => setPlaying(false);

    video.addEventListener('timeupdate', handleTimeUpdate);
    video.addEventListener('loadedmetadata', handleLoadedMetadata);
    video.addEventListener('ended', handleEnded);

    return () => {
      video.removeEventListener('timeupdate', handleTimeUpdate);
      video.removeEventListener('loadedmetadata', handleLoadedMetadata);
      video.removeEventListener('ended', handleEnded);
    };
  }, [onTimeUpdate]);

  const togglePlay = () => {
    const video = videoRef.current;
    if (!video) return;
    if (playing) video.pause();
    else video.play();
    setPlaying(!playing);
  };

  const formatTime = (time) => {
    if (!isFinite(time)) return '0:00';
    const mins = Math.floor(time / 60);
    const secs = Math.floor(time % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (!src) return (
    <div className={`video-player ${className} empty`} style={{ width, height, background: '#f4f7ff', border: '1px solid #dbe4ff', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#8892a4' }}>
      <span>No video source</span>
    </div>
  );

  return (
    <div className="video-player" style={{ width, height, background: '#f4f7ff', border: '1px solid #dbe4ff', borderRadius: '12px', overflow: 'hidden' }}>
      <video
        ref={videoRef}
        autoPlay={autoPlay}
        playsInline
        muted={autoPlay}
        style={{ width: '100%', height: '100%' }}
      />
      <div className="video-controls" style={{
        position: 'absolute',
        bottom: 0,
        left: 0,
        right: 0,
        background: 'rgba(23,32,92,0.4)',
        padding: '12px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        color: '#fff'
      }}>
        <div className="video-time" style={{
          display: 'flex',
          gap: '8px',
          fontSize: '12px',
          color: '#fff'
        }}>
          <span>{formatTime(currentTime)}</span>
          <span>/</span>
          <span>{formatTime(duration)}</span>
        </div>
        <div className="video-controls-right" style={{ display: 'flex', gap: '8px' }}>
          <button className="icon-button" onClick={togglePlay} aria-label={playing ? 'Pause' : 'Play'} style={{ width: 36, height: 36, display: 'grid', placeItems: 'center' }}>
            {playing ? <Pause size={20} /> : <Play size={20} />}
          </button>
          <button className="icon-button" onClick={() => video.currentTime = Math.max(0, video.currentTime - 15)} aria-label="Rewind 15s" style={{ width: 36, height: 36, display: 'grid', placeItems: 'center' }}><Rewind size={18} /></button>
          <button className="icon-button" onClick={() => video.currentTime = Math.min(video.duration, video.currentTime + 15)} aria-label="Forward 15s" style={{ width: 36, height: 36, display: 'grid', placeItems: 'center' }}><FastForward size={18} /></button>
        </div>
      </div>
    </div>
  );
}