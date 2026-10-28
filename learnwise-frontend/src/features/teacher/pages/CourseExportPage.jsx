import React, { useState } from 'react';
import { CheckCircle, Loader2, FileText, Download } from 'lucide-react';
import { coursesApi } from '../../../api/courses.api';
import { AppShell } from '../../../layouts/AppShell';
import { Button, PageHeader } from '../../../components/shared/Primitives';
import { ErrorState, LoadingState } from '../../../components/ui/States';
import '../../student/components/courses.css';

export function CourseExportPage({ courseId }) {
  const [exporting, setExporting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');

  React.useEffect(() => {
    if (!courseId) return;
  }, [courseId]);

  const handleExport = async () => {
    setExporting(true);
    setError('');
    setSuccess(false);
    try {
      const blob = await coursesApi.export(courseId);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `course_${courseId}_export_${new Date().toISOString().slice(0, 10)}.zip`;
      document.body.appendChild(link);
      link.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(link);
      setSuccess(true);
    } catch (err) {
      setError('Failed to export course. Please try again.');
    } finally {
      setExporting(false);
    }
  };

  if (!isBackendApiEnabled) {
    return (
      <AppShell>
        <PageHeader eyebrow="Course Export" title="Export Course" description="Export course as ZIP" />
        <ErrorState message="API disabled - connect to backend." />
      </AppShell>
    );
  }

  if (!courseId) {
    return (
      <AppShell>
        <PageHeader eyebrow="Course Export" title="Export Course" description="Course not found." />
      </AppShell>
    );
  }

  return (
    <AppShell>
      <PageHeader eyebrow="Course Export" title="Export Course" description="Download course as ZIP file" />
      {error && <ErrorState message={error} />}
      <div className="course-export">
        <div className="export-info">
          <h3 className="section-title">Course: {courseId}</h3>
          <p className="export-description">
            The ZIP file will contain course_metadata.json, chapters.json, materials.json, and a files/ folder with all material files.
          </p>
        </div>

        <div className="export-actions">
          {exporting && (
            <div className="exporting-state">
              <Loader2 size={32} /> Exporting…
            </div>
          )}
          {!exporting && (
            <Button onClick={handleExport} disabled={exporting} className="btn-course-primary export-btn">
              {exporting ? 'Exporting…' : 'Export Course as ZIP'}
            </Button>
          )}
          {success && (
            <p className="success-text">Export successful!</p>
          )}
        </div>
      </div>
    </AppShell>
  );
}
