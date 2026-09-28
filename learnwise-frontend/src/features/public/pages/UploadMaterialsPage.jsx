import React, { useEffect, useState } from 'react';
import { AlertCircle, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { FileUploader } from '../../../components/ui/FileUploader';
import { coursesApi } from '../../../api/courses.api';
import { isBackendApiEnabled } from '../../../api/client';
import { PublicFrame } from '../components/PublicFrame';

export function UploadMaterialsPage() {
  const [courses, setCourses] = useState([]);
  const [courseId, setCourseId] = useState(isBackendApiEnabled ? '' : 'demo-course');
  const [loading, setLoading] = useState(isBackendApiEnabled);
  const [error, setError] = useState('');
  useEffect(() => {
    if (!isBackendApiEnabled) return undefined;
    let active = true;
    coursesApi.list().then(response => {
      if (!active) return;
      const items = Array.isArray(response) ? response : response.results || [];
      setCourses(items);
      setCourseId(items[0]?.id || '');
    }).catch(() => {
      if (active) setError('Could not load your courses. Refresh or return to the course list and try again.');
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);
  return <PublicFrame><main className="upload-special"><span className="kicker">Teacher workspace</span><h1>Upload course materials.</h1><p>Attach a PDF, DOCX, or course audio file. In backend mode, Learnwise tracks upload, transcription, and summary processing separately.</p>{isBackendApiEnabled && <label className="upload-course-select">Course<select value={courseId} onChange={event => setCourseId(event.target.value)} disabled={loading || !courses.length}><option value="">{loading ? 'Loading courses…' : 'Choose a course'}</option>{courses.map(course => <option key={course.id} value={course.id}>{course.title}</option>)}</select></label>}{error && <p className="upload-error" role="alert"><AlertCircle size={16}/>{error}</p>}{!loading && !error && (!isBackendApiEnabled || courses.length > 0) && <FileUploader courseId={courseId} />}{isBackendApiEnabled && !loading && !error && !courses.length && <p className="state-panel">Create a course before uploading materials.</p>}<Link to="/teacher/materials" className="text-link">Back to materials <ArrowRight size={14}/></Link></main></PublicFrame>;
}
