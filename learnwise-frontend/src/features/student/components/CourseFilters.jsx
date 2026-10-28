import React from 'react';
import { Filter, Search, List, Layout } from 'lucide-react';
import '../components/courses.css';

export function CourseFilters({ 
  filterStatus, 
  setFilterStatus, 
  filterLevel, 
  setFilterLevel, 
  filterContentType, 
  setFilterContentType,
  filterLanguage, 
  setFilterLanguage,
  availableFilters,
  onApplyFilters
}) {
  const statusOptions = [
    { value: 'all', label: 'All status' },
    { value: 'published', label: 'Published' },
    { value: 'draft', label: 'Draft' },
    { value: 'archived', label: 'Archived' },
    { value: 'pending_review', label: 'Pending Review' },
  ];

  const levelOptions = [
    { value: 'all', label: 'All levels' },
    { value: 'beginner', label: 'Beginner' },
    { value: 'intermediate', label: 'Intermediate' },
    { value: 'advanced', label: 'Advanced' },
    { value: 'expert', label: 'Expert' },
  ];

  const contentTypeOptions = [
    { value: 'all', label: 'All types' },
    { value: 'video', label: 'Video' },
    { value: 'document', label: 'Document' },
    { value: 'audio', label: 'Audio' },
    { value: 'code', label: 'Code' },
  ];

  const languageOptions = [
    { value: 'all', label: 'All languages' },
    { value: 'en', label: 'English' },
    { value: 'fr', label: 'Français' },
    { value: 'es', label: 'Español' },
    { value: 'de', label: 'Deutsch' },
  ];

  return (
    <div className="course-filters">
      <h3 className="course-filters-title">Filter Courses</h3>

      <div className="course-filters-grid">
        {/* Status Filter */}
        <div className="course-filters-group">
          <label className="course-filters-label" htmlFor="filter-status">Status</label>
          <select
            className="course-filters-select"
            id="filter-status"
            value={filterStatus || 'all'}
            onChange={(e) => setFilterStatus(e.target.value)}
          >
            <option value="all">All statuses</option>
            {statusOptions.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        {/* Level Filter */}
        <div className="course-filters-group">
          <label className="course-filters-label" htmlFor="filter-level">Level</label>
          <select
            className="course-filters-select"
            id="filter-level"
            value={filterLevel || 'all'}
            onChange={(e) => setFilterLevel(e.target.value)}
          >
            <option value="all">All levels</option>
            {levelOptions.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        {/* Content Type Filter */}
        <div className="course-filters-group">
          <label className="course-filters-label" htmlFor="filter-content-type">Content Type</label>
          <select
            className="course-filters-select"
            id="filter-content-type"
            value={filterContentType || 'all'}
            onChange={(e) => setFilterContentType(e.target.value)}
          >
            <option value="all">All types</option>
            {contentTypeOptions.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        {/* Language Filter */}
        <div className="course-filters-group">
          <label className="course-filters-label" htmlFor="filter-language">Language</label>
          <select
            className="course-filters-select"
            id="filter-language"
            value={filterLanguage || 'all'}
            onChange={(e) => setFilterLanguage(e.target.value)}
          >
            <option value="all">All languages</option>
            {languageOptions.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="course-filters-actions">
        <button className="btn-course-primary" onClick={() => onApplyFilters()}>
          Apply Filters
        </button>
      </div>
    </div>
  );
}
