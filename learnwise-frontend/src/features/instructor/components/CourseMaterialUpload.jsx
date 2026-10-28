import React, { useState, useRef, useCallback } from 'react';
import { Loader2, Upload, AlertCircle, CheckCircle, FileText, Image, Menu } from 'lucide-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { coursesApi } from '../../../api/courses.api';
import { materialsApi } from '../../../api/materials.api';
import { isBackendApiEnabled } from '../../../api/client';
import { Button, ProgressBar } from '../../../components/shared/Primitives';
import { ErrorState, LoadingState, EmptyState } from '../../../components/ui/States';
import '../components/courses.css';

export function CourseMaterialUpload({ courseId, onMaterialAdded }) {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [progress, setProgress] = useState(0);
  const [showUpload, setShowUpload] = useState(false);
  const queryClient = useQueryClient();

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      setError('');
      setProgress(0);
      uploadFile(selectedFile);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const selectedFile = e.dataTransfer.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      setError('');
      setProgress(0);
      uploadFile(selectedFile);
    }
  };

  const uploadFile = async (file) => {
    setUploading(true);
    setError('');
    setProgress(0);

    try {
      const formData = new FormData();
      formData.append('course', courseId);
      formData.append('title', file.name.replace(/\.[^/.]+$/, ''));
      formData.append('file', file);
      formData.append('material_type', 'document');

      // Upload with progress tracking
      const xhr = new XMLHttpRequest();
      xhr.open('POST', '/api/content/materials/', true);
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) {
          const percent = Math.round((e.loaded / e.total) * 100);
          setProgress(percent);
        }
      };
      xhr.onerror = () => {
        setError('Failed to upload file. Please try again.');
        setUploading(false);
      };
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          const response = JSON.parse(xhr.responseText);
          queryClient.invalidateQueries(['content', 'materials', courseId]);
          if (onMaterialAdded) onMaterialAdded(response);
          setFile(null);
          setProgress(0);
          setUploading(false);
        } else {
          setError('Upload failed. Server responded with status: ' + xhr.status);
          setUploading(false);
        }
      };
      xhr.send(formData);
    } catch (err) {
      setError('Upload failed. Please try again.');
      setUploading(false);
    }
  };

  if (!isBackendApiEnabled) {
    return (
      <EmptyState
        title="File upload (preview mode)"
        description="Connect to the backend API to enable file upload functionality."
        action={() => setShowUpload(true)}
      />
    );
  }

  return (
    <div style={{
      background: '#fff',
      border: '1px solid #dbe4ff',
      borderRadius: '12px',
      padding: '24px',
      marginBottom: '24px',
      boxShadow: '0 24px 60px -16px rgba(23,32,92,0.16)',
      maxWidth: '620px',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
        <Image size={24} className="course-icon" style={{ color: '#57d8ff' }} />
        <span style={{ fontFamily: '"Inter", system-ui, -apple-system, Segoe UI, Roboto, sans-serif', color: '#17205c', fontSize: '14px' }}>Add Course Material</span>
      </div>

      <p style={{ fontSize: '13px', color: '#687281', margin: '0 0 16px' }}>
        Support files: PDF, DOC, DOCX, PPT, PPTX, TXT, Images (JPG, PNG, WebP). Max 50MB.
      </p>

      <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
        <input
          type="file"
          accept=".pdf,.doc,.docx,.ppt,.pptx,.txt,.jpg,.png,.webp"
          onChange={handleFileChange}
          style={{
            display: 'none'
          }}
        />
        <label htmlFor="file-upload" style={{
          cursor: 'pointer',
          display: 'inline-flex',
          alignItems: 'center',
          gap: '8px',
          padding: '10px 16px',
          background: '#f4f7ff',
          border: '1px solid #dbe4ff',
          borderRadius: '10px',
          fontFamily: '"Inter", system-ui, -apple-system, Segoe UI, Roboto, sans-serif',
          fontSize: '13px',
          color: '#57d8ff',
          transition: 'background 0.2s'
        }}>
          <Upload size={18} /> Drag & drop or browse files
        </label>
      </div>

      {file && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
          <Image size={32} className="course-icon" style={{ color: '#57d8ff' }} />
          <span style={{ fontFamily: '"Inter", system-ui, -apple-system, Segoe UI, Roboto, sans-serif', color: '#17205c', fontSize: '14px' }}>{file.name}</span>
          <ProgressBar value={progress} size="sm" />
          <button
            onClick={() => {
              const reader = new FileReader();
              reader.onload = () => {
                // Just reset file state without uploading
                setFile(null);
                setProgress(0);
              };
              reader.readAsDataURL(file);
            }}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#57d8ff',
              fontSize: '12px',
              cursor: 'pointer'
            }}>
            Cancel
          </button>
        </div>
      )}

      {uploading && (
        <ProgressBar value={progress} size="sm" className="mb-2" />
      )}

      {error && (
        <p style={{ color: '#d14343', fontSize: '13px', margin: '8px 0 0' }}>{error}</p>
      )}

      <button
        onClick={() => setShowUpload(true)
        }
        style={{
          width: '100%',
          marginTop: '16px',
          padding: '10px',
          background: 'linear-gradient(135deg,#57d8ff,#ff4f87)',
          border: 'none',
          borderRadius: '8px',
          color: '#fff',
          fontFamily: '"Inter", system-ui, -apple-system, Segoe UI, Roboto, sans-serif',
          fontSize: '13px',
          fontWeight: '600',
          cursor: 'pointer'
        }}
      >
        {uploading ? 'Uploading…' : 'Upload Material'}
      </button>
    </div>
  );
}