import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { CourseFilters } from '../src/features/student/components/CourseFilters';

describe('CourseFilters', () => {
  const onApplyFilters = jest.fn();

  const renderFilters = (props = {}) =>
    render(
      <MemoryRouter>
        <CourseFilters
          filterStatus="all"
          setFilterStatus={jest.fn()}
          filterLevel="all"
          setFilterLevel={jest.fn()}
          filterContentType="all"
          setFilterContentType={jest.fn()}
          filterLanguage="all"
          setFilterLanguage={jest.fn()}
          onApplyFilters={onApplyFilters}
          {...props}
        />
      </MemoryRouter>
    );

  test('renders all filter dropdowns', () => {
    renderFilters();
    expect(screen.getByRole('combobox', { name: /status/i })).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: /level/i })).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: /content type/i })).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: /language/i })).toBeInTheDocument();
  });

  test('renders Apply Filters button', () => {
    renderFilters();
    expect(screen.getByText('Apply Filters')).toBeInTheDocument();
  });

  test('status filter changes on select', () => {
    const setFilterStatus = jest.fn();
    renderFilters({ setFilterStatus });
    const statusSelect = screen.getByRole('combobox', { name: /status/i });
    fireEvent.change(statusSelect, { target: { value: 'published' } });
    expect(setFilterStatus).toHaveBeenCalledWith('published');
  });

  test('level filter changes on select', () => {
    const setFilterLevel = jest.fn();
    renderFilters({ setFilterLevel });
    const levelSelect = screen.getByRole('combobox', { name: /level/i });
    fireEvent.change(levelSelect, { target: { value: 'advanced' } });
    expect(setFilterLevel).toHaveBeenCalledWith('advanced');
  });

  test('content type filter changes on select', () => {
    const setFilterContentType = jest.fn();
    renderFilters({ setFilterContentType });
    const contentTypeSelect = screen.getByRole('combobox', { name: /content type/i });
    fireEvent.change(contentTypeSelect, { target: { value: 'video' } });
    expect(setFilterContentType).toHaveBeenCalledWith('video');
  });

  test('language filter changes on select', () => {
    const setFilterLanguage = jest.fn();
    renderFilters({ setFilterLanguage });
    const languageSelect = screen.getByRole('combobox', { name: /language/i });
    fireEvent.change(languageSelect, { target: { value: 'fr' } });
    expect(setFilterLanguage).toHaveBeenCalledWith('fr');
  });

  test('apply filters button calls onApplyFilters', () => {
    renderFilters();
    fireEvent.click(screen.getByText('Apply Filters'));
    expect(onApplyFilters).toHaveBeenCalledTimes(1);
  });
});
