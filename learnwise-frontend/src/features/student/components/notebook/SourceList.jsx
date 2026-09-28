import React, { useRef } from 'react';
import { Check, FileAudio, FileText, Plus, Upload } from 'lucide-react';

const sourceName = source => typeof source === 'string' ? source : source.title || source.file_name || source.name || 'Untitled source';
const sourceId = source => typeof source === 'string' ? source : source.id;
const isAudio = source => /\.(mp3|wav)$/i.test(sourceName(source)) || source.kind === 'audio';
const isReady = source => typeof source === 'string' || !source.status || source.status === 'completed';
const iconFor = source => isAudio(source) ? <FileAudio size={17}/> : <FileText size={17}/>;

export function SourceList({ sources, selectedSources = [], onToggle = () => {}, onSelectAll = () => {}, onAdd, canUpload = true }) {
  const inputRef = useRef(null);
  const selectFile = event => {
    const file = event.target.files?.[0];
    if (file) onAdd(file);
    event.target.value = '';
  };
  const selectableSources = sources.filter(isReady);
  const allSelected = Boolean(selectableSources.length) && selectableSources.every(source => selectedSources.includes(sourceId(source)));
  return <section className="notebook-sources" aria-labelledby="sources-heading">
    {canUpload && <input ref={inputRef} type="file" accept=".pdf,.mp3,.wav,.docx" hidden onChange={selectFile}/>}
    <div className="notebook-section-head">
      <div><span className="eyebrow">SOURCES</span><h2 id="sources-heading">Source library</h2></div>
      {canUpload && <button type="button" className="notebook-icon-action" onClick={() => inputRef.current?.click()} aria-label="Add source"><Plus size={17}/></button>}
    </div>
    <p className="notebook-muted">Choose the material you want your notebook to use.</p>
    <div className="source-selection-bar">
      <span>{selectedSources.length} of {sources.length} selected</span>
      <button type="button" disabled={!selectableSources.length} onClick={() => onSelectAll(!allSelected)}>{allSelected ? 'Clear all' : 'Select all'}</button>
    </div>
    <div className="source-list">
      {sources.map((source, index) => {
        const id = sourceId(source);
        const selected = selectedSources.includes(id);
        const ready = isReady(source);
        return <button type="button" id={`source-${id}`} className={`source-row ${selected ? 'selected' : ''}`} key={`${id}-${index}`} aria-pressed={selected} disabled={!ready} onClick={() => onToggle(id)}>
          <span className="source-check" aria-hidden="true">{selected && <Check size={13}/>}</span>
          <span className="source-type-icon">{iconFor(source)}</span>
          <span className="source-copy"><b>{sourceName(source)}</b><small>{ready ? isAudio(source) ? 'Audio source' : 'Document source' : `${source.status || 'Processing'}${Number.isFinite(source.progress) ? ` · ${source.progress}%` : ''}`}</small></span>
        </button>;
      })}
      {!sources.length && <p className="notebook-no-sources">{canUpload ? 'Add a PDF, audio file, or DOCX to begin.' : 'Course materials will appear here when available.'}</p>}
    </div>
    {canUpload && <button type="button" className="source-dropzone" onClick={() => inputRef.current?.click()}><Upload size={17}/><span>Add a source</span></button>}
  </section>;
}
