import React from 'react';
import { ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import '../components/courses.css';

export function CourseCard({ course }) {
  const progress = course.progress || 0;
  const status = course.status || 'published';

  return (
    <Link to={`/student/courses/${course.id}`} className="course-card">
      <div className="course-thumbnail">
        <span className="course-icon">{course.icon || '✦'}</span>
        <small className="course-category">{course.category || 'Course'}</small>
        <div className="thumbnail-lines">
          <i />
          <i />
          <i />
        </div>
      </div>
      <div className="course-card-body">
        <div className="course-title-row">
          <h3 className="course-title">{course.title}</h3>
          <span className={`course-status-badge course-status-badge-${status}`}>{status.charAt(0).toUpperCase() + status.slice(1)}</span>
        </div>
        <p className="course-instructor">{course.instructor || 'Learnwise educator'}</p>
        <div className="course-progress">
          <div className="progress-track">
            <div className="progress-fill" style={{ width: `${Math.min(progress, 100)}%` }} />
          </div>
          <span className="progress-percentage">{Math.min(progress, 100)}%</span>
        </div>
        <div className="course-foot">
          <span>{course.lessons || 0} lessons</span>
          <span className="continue-label">
            <ArrowRight size={13} /> Continue
          </span>
        </div>
      </div>
    </Link>
  );
}