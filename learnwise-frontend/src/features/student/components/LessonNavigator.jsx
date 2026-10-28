import React from 'react';
import { ArrowRight, Book, Layout, Folder } from 'lucide-react';
import '../components/courses.css';

const ICON_MAP = {
  video: '🎬',
  audio: '🎧',
  document: '📄',
  code: '💻',
};

export function LessonNavigator({ course, selectedMaterial, onMaterialSelect }) {
  const renderBreadcrumb = () => (
    <nav className="course-curriculum-breadcrumb">
      <span>Learnwise</span>
      <span>/</span>
      <span> {course.title}</span>
    </nav>
  );

  const renderChapterSidebar = () => {
    if (!course || !course.chapters || course.chapters.length === 0) return null;

    return (
      <div className="course-curriculum">
        <h3>Course Chapters</h3>
        {course.chapters.map((chapter, idx) => (
          <div key={chapter.id} className="course-chapter">
            <div className="course-chapter-header" onClick={() => onMaterialSelect?.(chapter.id)}>
              <h4 className="course-chapter-title">
                {chapter.order}. {chapter.title}
              </h4>
              <span className="course-chapter-toggle">▾</span>
            </div>
            <div className="course-chapter-items">
              {chapter.materials?.map((material, mIdx) => (
                <div
                  key={material.id}
                  className={`course-chapter-item ${selectedMaterial === material.id ? 'active' : ''} kind-${material.kind}`}
                  onClick={() => onMaterialSelect?.(material.id)}
                >
                  <span className="course-chapter-item-icon">
                    {ICON_MAP[material.kind] || '📄'}
                  </span>
                  <span className="course-chapter-item-title">{material.title || 'Untitled'}</span>
                  <span className={`course-chapter-item-status ${material.status === 'completed' ? 'completed' : ''}`}>
                    {material.status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div>
      {renderBreadcrumb()}
      {renderChapterSidebar()}
    </div>
  );
}
