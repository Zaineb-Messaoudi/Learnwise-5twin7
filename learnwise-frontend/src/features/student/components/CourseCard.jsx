import React from 'react';
import { ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { ProgressBar } from '../../../components/shared/Primitives';

export function CourseCard({ course }) {
  return <Link to={`/student/courses/${course.id}`} className="course-card"><div className={`course-thumbnail art-${course.color}`}><span>{course.icon}</span><small>{course.category}</small><div className="thumbnail-lines"><i/><i/><i/></div></div><div className="course-card-body"><div className="course-title-row"><h3>{course.title}</h3></div><p>{course.instructor} <span>·</span> {course.level}</p><div className="course-progress"><ProgressBar value={course.progress}/><span>{course.progress}%</span></div><div className="course-foot"><span>{course.lessons} lessons</span><span className="continue-label">Continue <ArrowRight size={13}/></span></div></div></Link>;
}
