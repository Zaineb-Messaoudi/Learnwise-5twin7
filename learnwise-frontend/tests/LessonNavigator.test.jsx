import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { LessonNavigator } from '../src/features/student/components/LessonNavigator';

describe('LessonNavigator', () => {
  const baseCourse = {
    id: 'course-1',
    title: 'Neural Networks Basics',
    chapters: [
      {
        id: 'chapter-1',
        title: 'Foundations',
        description: 'Introduction to neural networks',
        order: 1,
        materials: [
          { id: 'mat-1', title: 'Perceptrons', kind: 'document', status: 'completed' },
          { id: 'mat-2', title: 'Activation Functions', kind: 'video', status: 'in_progress' },
        ],
      },
      {
        id: 'chapter-2',
        title: 'Backpropagation',
        description: 'Training neural networks',
        order: 2,
        materials: [
          { id: 'mat-3', title: 'Gradient Descent', kind: 'audio', status: 'draft' },
        ],
      },
    ],
  };

  const onMaterialSelect = jest.fn();

  const renderNavigator = (course = baseCourse, selectedMaterial = null) =>
    render(
      <MemoryRouter>
        <LessonNavigator course={course} selectedMaterial={selectedMaterial} onMaterialSelect={onMaterialSelect} />
      </MemoryRouter>
    );

  test('renders course title in breadcrumb', () => {
    renderNavigator();
    expect(screen.getByText('Neural Networks Basics')).toBeInTheDocument();
  });

  test('renders chapter titles', () => {
    renderNavigator();
    expect(screen.getByText('1. Foundations')).toBeInTheDocument();
    expect(screen.getByText('2. Backpropagation')).toBeInTheDocument();
  });

  test('renders chapter order numbers', () => {
    renderNavigator();
    expect(screen.getByText('1. Foundations')).toBeInTheDocument();
    expect(screen.getByText('2. Backpropagation')).toBeInTheDocument();
  });

  test('renders material titles within chapters', () => {
    renderNavigator();
    expect(screen.getByText('Perceptrons')).toBeInTheDocument();
    expect(screen.getByText('Activation Functions')).toBeInTheDocument();
    expect(screen.getByText('Gradient Descent')).toBeInTheDocument();
  });

  test('calls onMaterialSelect when clicking a material', () => {
    renderNavigator();
    fireEvent.click(screen.getByText('Perceptrons'));
    expect(onMaterialSelect).toHaveBeenCalledWith('mat-1');
  });

  test('renders kind icons for materials', () => {
    renderNavigator();
    expect(screen.getByText('📄')).toBeInTheDocument(); // document
    expect(screen.getByText('🎬')).toBeInTheDocument(); // video
    expect(screen.getByText('🎧')).toBeInTheDocument(); // audio
  });

  test('shows completed status on completed materials', () => {
    renderNavigator();
    expect(screen.getByText('completed')).toBeInTheDocument();
  });

  test('renders breadcrumb navigation', () => {
    renderNavigator();
    expect(screen.getByText('Learnwise')).toBeInTheDocument();
  });

  test('renders nothing for chapters when course has no chapters', () => {
    const { container } = render(
      <MemoryRouter>
        <LessonNavigator course={{ id: 'course-1', title: 'Empty Course', chapters: [] }} selectedMaterial={null} onMaterialSelect={onMaterialSelect} />
      </MemoryRouter>
    );
    expect(container.querySelector('.course-curriculum')).not.toBeInTheDocument();
  });
});
