import React, { useState } from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { NotebookChat } from '../src/features/student/components/notebook/NotebookChat';
import { SourceList } from '../src/features/student/components/notebook/SourceList';
import { StudioPanel } from '../src/features/student/components/notebook/StudioPanel';

function SourcePicker() {
  const [selected, setSelected] = useState(['Backpropagation.pdf']);
  const sources = ['Backpropagation.pdf', 'Lecture.mp3'];
  const toggle = source => setSelected(current => current.includes(source) ? current.filter(item => item !== source) : [...current, source]);
  return <SourceList sources={sources} selectedSources={selected} onToggle={toggle} onSelectAll={value => setSelected(value ? sources : [])} onAdd={jest.fn()} />;
}

describe('notebook workspace interactions', () => {
  test('source list supports selecting one or all source files', () => {
    render(<SourcePicker />);
    const pdf = screen.getByRole('button', { name: /Backpropagation.pdf/ });
    expect(pdf).toHaveAttribute('aria-pressed', 'true');
    fireEvent.click(screen.getByRole('button', { name: /Lecture.mp3/ }));
    expect(screen.getByText('2 of 2 selected')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Clear all' }));
    expect(screen.getByText('0 of 2 selected')).toBeInTheDocument();
  });

  test('unprocessed sources cannot be selected for grounded requests', () => {
    const onSelectAll = jest.fn();
    render(<SourceList
      sources={[
        { id: 'material-ready', title: 'Ready.pdf', status: 'completed' },
        { id: 'material-pending', title: 'Pending.pdf', status: 'processing' },
      ]}
      selectedSources={[]}
      onSelectAll={onSelectAll}
    />);
    expect(screen.getByRole('button', { name: /Pending.pdf/ })).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: 'Select all' }));
    expect(onSelectAll).toHaveBeenCalledWith(true);
  });

  test('chat suggestions submit a prompt to the assistant handler', () => {
    const onAsk = jest.fn();
    render(<NotebookChat notebook={{ title: 'Learning notebook' }} selectedSources={['material-1']} onAsk={onAsk} onSourcesClick={jest.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: 'What are the key ideas?' }));
    expect(onAsk).toHaveBeenCalledWith('What are the key ideas?');
    expect(screen.getByText('What would you like to explore?')).toBeInTheDocument();
  });

  test('chat renders the assistant response and citations returned by the API', () => {
    render(<NotebookChat
      notebook={{ title: 'Learning notebook' }}
      selectedSources={['material-1']}
      messages={[
        { id: 'user-1', role: 'user', content: 'What are the key ideas?' },
        { id: 'assistant-1', role: 'assistant', content: 'The course explains gradient descent.', citations: [{ id: 'material-1', title: 'Backpropagation.pdf', page: 4 }] },
      ]}
      onAsk={jest.fn()}
      onSourcesClick={jest.fn()}
    />);
    expect(screen.getByText('The course explains gradient descent.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Backpropagation.pdf/ })).toBeInTheDocument();
  });

  test('studio exposes notebook study tools and handles audio action', () => {
    const onAudio = jest.fn();
    render(<StudioPanel onAudio={onAudio} />);
    fireEvent.click(screen.getByRole('button', { name: /Audio overview/ }));
    expect(onAudio).toHaveBeenCalledTimes(1);
    expect(screen.getByRole('button', { name: /Mind map/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Flashcards/ })).toBeInTheDocument();
  });

  test('studio sends selected tool generation to its handler', () => {
    const onCreate = jest.fn();
    render(<StudioPanel onCreate={onCreate} />);
    fireEvent.click(screen.getByRole('button', { name: /Mind map/ }));
    expect(onCreate).toHaveBeenCalledWith('mind_map');
  });
});
