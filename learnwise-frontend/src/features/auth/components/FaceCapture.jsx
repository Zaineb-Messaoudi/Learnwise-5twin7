import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Video, Loader2, AlertCircle, CheckCircle, X, Upload, Camera, Eye, EyeOff } from 'lucide-react';
import * as faceapi from 'face-api.js';

import './FaceCapture.css';

const getModelUrl = () => `${window.location.origin}/models`;

export function FaceCapture({
  onCapture,
  onError,
  required = true,
  showPreview = true,
  mode = 'both', // 'camera' | 'upload' | 'both'
  defaultMode = 'camera',
}) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const fileInputRef = useRef(null);
  const [status, setStatus] = useState('loading');
  const [error, setError] = useState(null);
  const [descriptor, setDescriptor] = useState(null);
  const [quality, setQuality] = useState(0);
  const [faceDetected, setFaceDetected] = useState(false);
  const [captureMode, setCaptureMode] = useState(defaultMode);
  const [imagePreview, setImagePreview] = useState(null);
  const [isCapturing, setIsCapturing] = useState(false);
  const [captureFeedback, setCaptureFeedback] = useState(null);
  const modelsLoaded = useRef(false);
  const detectionInterval = useRef(null);
  const streamRef = useRef(null);
  const isProcessing = useRef(false);
  const onErrorRef = useRef(onError);
  onErrorRef.current = onError;

  const loadModels = useCallback(async () => {
    if (modelsLoaded.current) return;
    const modelUrl = getModelUrl();
    try {
      await Promise.all([
        faceapi.nets.tinyFaceDetector.loadFromUri(modelUrl),
        faceapi.nets.faceLandmark68Net.loadFromUri(modelUrl),
        faceapi.nets.faceRecognitionNet.loadFromUri(modelUrl),
        faceapi.nets.faceExpressionNet.loadFromUri(modelUrl),
      ]);
      modelsLoaded.current = true;
      setStatus('ready');
    } catch (err) {
      setError('Failed to load face recognition models. Please refresh the page.');
      setStatus('error');
      onErrorRef.current?.(err);
    }
  }, []);

  const startCamera = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480, facingMode: 'user' },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
    } catch (err) {
      setError('Camera access denied. Please allow camera permission or use photo upload.');
      setStatus('error');
      onError?.(err);
    }
  }, [onError]);

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    if (detectionInterval.current) {
      clearInterval(detectionInterval.current);
      detectionInterval.current = null;
    }
  }, []);

  const processImageFile = useCallback(async (file) => {
    if (isProcessing.current) return;
    isProcessing.current = true;
    
    try {
      if (!file.type.startsWith('image/')) {
        throw new Error('Please select a valid image file (JPEG, PNG, WebP).');
      }
      if (file.size > 5 * 1024 * 1024) {
        throw new Error('Image must be less than 5MB.');
      }

      const img = new Image();
      img.src = URL.createObjectURL(file);
      await new Promise((resolve, reject) => {
        img.onload = resolve;
        img.onerror = () => reject(new Error('Failed to load image.'));
      });

      const detection = await faceapi
        .detectSingleFace(img, new faceapi.TinyFaceDetectorOptions())
        .withFaceLandmarks()
        .withFaceDescriptor()
        .withFaceExpressions();

      URL.revokeObjectURL(img.src);

      if (!detection) {
        throw new Error('No face detected in the image. Please upload a clear photo of your face.');
      }

      const { descriptor, expressions, detection: det } = detection;
      const box = det.box;
      const faceArea = box.width * box.height;
      const imgArea = img.width * img.height;
      const coverage = faceArea / imgArea;

      let qualityScore = Math.min(1, coverage * 4);
      if (expressions.neutral > 0.6) qualityScore *= 1.2;
      if (expressions.happy > 0.3) qualityScore *= 1.1;
      qualityScore = Math.min(1, Math.max(0, qualityScore));

      setQuality(qualityScore);

      if (qualityScore < 0.3) {
        throw new Error('Photo quality too low. Ensure good lighting, face is visible, and neutral expression.');
      }

      const descArray = Array.from(descriptor);
      setDescriptor(descArray);
      
      const canvas = document.createElement('canvas');
      canvas.width = img.width;
      canvas.height = img.height;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(img, 0, 0);
      const dataUrl = canvas.toDataURL('image/png');
      
      setImagePreview(dataUrl);
      onCapture?.(descArray, qualityScore, dataUrl);
      setStatus('captured');
    } catch (err) {
      setError(err.message || 'Failed to process image. Please try another photo.');
      setStatus('error');
      onError?.(err);
    } finally {
      isProcessing.current = false;
    }
  }, [onCapture, onError]);

  const handleFileSelect = useCallback((e) => {
    const file = e.target.files?.[0];
    if (file) {
      setStatus('processing');
      setError(null);
      processImageFile(file);
    }
  }, [processImageFile]);

  // Live preview only — updates the quality indicator. Does NOT auto-capture.
  const detectFace = useCallback(async () => {
    if (!videoRef.current || videoRef.current.readyState !== 4) return;

    try {
      const detection = await faceapi
        .detectSingleFace(videoRef.current, new faceapi.TinyFaceDetectorOptions())
        .withFaceExpressions();

      if (detection) {
        setFaceDetected(true);
        const box = detection.detection.box;
        const faceArea = box.width * box.height;
        const frameArea = videoRef.current.videoWidth * videoRef.current.videoHeight;
        const coverage = faceArea / frameArea;

        let qualityScore = Math.min(1, coverage * 4);
        const { expressions } = detection;
        if (expressions.neutral > 0.6) qualityScore *= 1.2;
        if (expressions.happy > 0.3) qualityScore *= 1.1;
        qualityScore = Math.min(1, Math.max(0, qualityScore));

        setQuality(qualityScore);
      } else {
        setFaceDetected(false);
        setQuality(0);
      }
    } catch (err) {
      console.error('Face detection error:', err);
    }
  }, []);

  // Explicit "Take Photo" action — runs the full detection + descriptor
  // extraction once, on demand, instead of auto-firing from the live loop.
  const capturePhoto = useCallback(async () => {
    if (!videoRef.current || videoRef.current.readyState !== 4 || isCapturing) return;
    setIsCapturing(true);
    setCaptureFeedback(null);

    try {
      const detection = await faceapi
        .detectSingleFace(videoRef.current, new faceapi.TinyFaceDetectorOptions())
        .withFaceLandmarks()
        .withFaceDescriptor()
        .withFaceExpressions();

      if (!detection) {
        setCaptureFeedback('No face detected. Center your face in the oval and try again.');
        return;
      }

      const { descriptor, expressions, detection: det } = detection;
      const box = det.box;
      const faceArea = box.width * box.height;
      const frameArea = videoRef.current.videoWidth * videoRef.current.videoHeight;
      const coverage = faceArea / frameArea;

      let qualityScore = Math.min(1, coverage * 4);
      if (expressions.neutral > 0.6) qualityScore *= 1.2;
      if (expressions.happy > 0.3) qualityScore *= 1.1;
      qualityScore = Math.min(1, Math.max(0, qualityScore));
      setQuality(qualityScore);

      const descArray = Array.from(descriptor);
      setDescriptor(descArray);

      if (canvasRef.current) {
        const ctx = canvasRef.current.getContext('2d');
        canvasRef.current.width = videoRef.current.videoWidth;
        canvasRef.current.height = videoRef.current.videoHeight;
        ctx.drawImage(videoRef.current, 0, 0);
        const dataUrl = canvasRef.current.toDataURL('image/png');
        onCapture?.(descArray, qualityScore, dataUrl);
        stopCamera();
        setStatus('captured');
      }
    } catch (err) {
      console.error('Face capture error:', err);
      setCaptureFeedback('Something went wrong capturing your photo. Please try again.');
      onErrorRef.current?.(err);
    } finally {
      setIsCapturing(false);
    }
  }, [onCapture, stopCamera, isCapturing]);

  useEffect(() => {
    loadModels();
  }, [loadModels]);

  useEffect(() => {
    if (status === 'ready' && captureMode === 'camera') {
      startCamera().then(() => {
        detectionInterval.current = setInterval(detectFace, 100);
      });
    }
    return () => {
      stopCamera();
      if (detectionInterval.current) clearInterval(detectionInterval.current);
    };
  }, [status, captureMode, startCamera, detectFace, stopCamera]);

  const switchMode = (mode) => {
    stopCamera();
    setCaptureMode(mode);
    setImagePreview(null);
    setQuality(0);
    setDescriptor(null);
    setError(null);
    setCaptureFeedback(null);
    if (mode === 'camera') {
      setStatus('ready');
      startCamera().then(() => {
        detectionInterval.current = setInterval(detectFace, 100);
      });
    } else {
      setStatus('ready');
    }
  };

  if (status === 'loading') {
    return (
      <div className="face-capture" role="status" aria-live="polite">
        <div className="face-capture-loading">
          <Loader2 size={32} className="spin" />
          <p>Loading photo tools…</p>
        </div>
      </div>
    );
  }

  if (status === 'error') {
    return (
      <div className="face-capture" role="alert">
        <div className="face-capture-error">
          <AlertCircle size={32} />
          <p>{error || 'Photo tools unavailable'}</p>
          <button onClick={() => { setStatus('loading'); loadModels(); }} className="btn-retry">
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (status === 'captured') {
    return (
      <div className="face-capture" role="status" aria-live="polite">
        <div className="face-capture-success">
          <CheckCircle size={48} className="success-icon" />
          <h3>Photo captured successfully</h3>
          <p>Quality score: {(quality * 100).toFixed(0)}%</p>
          {showPreview && imagePreview && (
            <img src={imagePreview} alt="Captured face" className="face-preview-img" />
          )}
          <button className="btn-retake" onClick={() => {
            setStatus('ready');
            setImagePreview(null);
            setQuality(0);
            setDescriptor(null);
            setCaptureFeedback(null);
            if (captureMode === 'camera') {
              startCamera().then(() => {
                detectionInterval.current = setInterval(detectFace, 100);
              });
            }
          }}>
            Retake
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="face-capture" role="region" aria-label="Face capture">
      {mode === 'both' && (
        <div className="face-mode-tabs">
          <button
            className={`face-mode-tab ${captureMode === 'camera' ? 'active' : ''}`}
            onClick={() => switchMode('camera')}
            disabled={status !== 'ready' && status !== 'captured'}
          >
            <Camera size={18} />
            <span>Camera</span>
          </button>
          <button
            className={`face-mode-tab ${captureMode === 'upload' ? 'active' : ''}`}
            onClick={() => switchMode('upload')}
            disabled={status !== 'ready' && status !== 'captured'}
          >
            <Upload size={18} />
            <span>Upload Photo</span>
          </button>
        </div>
      )}

      {captureMode === 'camera' && (
        <div className={`face-camera-view ${faceDetected ? 'face-scanning' : ''}`}>
          <div className="face-video-wrapper">
            <div className="face-scan-line" />
            <video
              ref={videoRef}
              autoPlay
              muted
              playsInline
              className="face-video"
              aria-hidden="true"
            />
            <canvas ref={canvasRef} className="face-overlay" aria-hidden="true" />
            <div className="face-guide">
              <div
                className={`face-oval ${faceDetected ? 'detected' : ''} ${
                  quality > 0.5 ? 'good' : quality > 0.2 ? 'fair' : 'poor'
                }`}
              />
              <p className="face-instruction">
                {faceDetected ? 'Hold steady — ready to capture' : 'Position your face within the oval'}
              </p>
            </div>
            <div className={`face-quality-indicator ${quality > 0.5 ? 'good' : quality > 0.2 ? 'fair' : 'poor'}`}>
              <span className="quality-bar">
                <span style={{ width: `${quality * 100}%` }} />
              </span>
              <span className="quality-text">
                {quality > 0.5 ? 'Good - Hold still' : quality > 0.2 ? 'Move closer' : 'Adjust position'}
              </span>
            </div>

            {captureFeedback && (
              <p className={`face-feedback ${quality < 0.3 ? 'warn' : 'info'}`}>{captureFeedback}</p>
            )}

            <button
              className={`btn-take-photo ${isCapturing ? 'capturing' : ''}`}
              onClick={capturePhoto}
              disabled={isCapturing}
            >
              {isCapturing ? 'Capturing…' : 'Take Photo'}
            </button>

          </div>
          <p className="face-hint">
            Ensure good lighting, look directly at the camera, and keep a neutral expression.
          </p>
        </div>
      )}

      {captureMode === 'upload' && (
        <div className="face-upload-view">
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleFileSelect}
            className="face-file-input"
            id="face-upload-input"
            disabled={status === 'processing'}
          />
          <label htmlFor="face-upload-input" className="face-upload-area">
            <Upload size={48} />
            <p>Drag & drop a photo or click to browse</p>
            <span className="upload-hint">JPEG, PNG, WebP • Max 5MB • Photo must be clearly visible</span>
          </label>
          {imagePreview && (
            <div className="face-upload-preview">
              <img src={imagePreview} alt="Preview" />
              <p>Quality: {(quality * 100).toFixed(0)}%</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default FaceCapture;