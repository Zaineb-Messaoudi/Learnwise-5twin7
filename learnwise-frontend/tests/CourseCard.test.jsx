import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { CourseCard } from '../src/features/student/components/CourseCard';

describe('CourseCard', () => {
  const baseCourse = {
    id: 'course-1',
    title: 'Introduction to Machine Learning',
    description: 'Learn the basics of ML',
    instructor: 'Dr. Smith',
    level: 'Beginner',
    status: 'published',
    progress: 45,
    lessons: 12,
    category: 'Data Science',
    icon: '🎓',
  };

  const renderCard = (course = baseCourse) =>
    render(<MemoryRouter><CourseCard course={course} /></MemoryRouter>);

  test('renders course title and icon', () => {
    renderCard();
    expect(screen.getByText('Introduction to Machine Learning')).toBeInTheDocument();
    expect(screen.getByText('🎓')).toBeInTheDocument();
  });

  test('renders course instructor and progress', () => {
    renderCard();
    expect(screen.getByText('Dr. Smith')).toBeInTheDocument();
    expect(screen.getByText('45%')).toBeInTheDocument();
  });

  test('renders lessons count', () => {
    renderCard();
    expect(screen.getByText('12 lessons')).toBeInTheDocument();
  });

  test('renders category badge', () => {
    renderCard();
    expect(screen.getByText('Data Science')).toBeInTheDocument();
  });

  test('renders status badge', () => {
    renderCard();
    expect(screen.getByText('Published')).toBeInTheDocument();
  });

  test('renders draft status correctly', () => {
    renderCard({ ...baseCourse, status: 'draft' });
    expect(screen.getByText('Draft')).toBeInTheDocument();
  });

  test('progress bar width reflects progress percentage', () => {
    const { container } = renderCard();
    const progressFill = container.querySelector('.progress-fill');
    expect(progressFill).toHaveStyle('width: 45%');
  });

  test('cap progress at 100%', () => {
    const { container } = renderCard({ ...baseCourse, progress: 150 });
    const progressFill = container.querySelector('.progress-fill');
    expect(progressFill).toHaveStyle('width: 100%');
    expect(screen.getByText('100%')).toBeInTheDocument();
  });

  test('renders link to course detail page', () => {
    const { container } = renderCard();
    const link = container.querySelector('a');
    expect(link).toHaveAttribute('href', '/student/courses/course-1');
  });
});
