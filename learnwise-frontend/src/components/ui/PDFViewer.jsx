import React, { useEffect, useRef, useState, useCallback } from 'react';
import { ChevronLeft, ChevronRight, Search, Download, RotateCcw, Maximize2, Minimize2, FileText, Sparkles } from 'lucide-react';

export function PDFViewer({
  src,
  transcript = null,
  summary = null,
  onPageChange,
  onTranscriptSelect,
  className = ''
}) {
  const [numPages, setNumPages] = useState(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [scale, setScale] = useState(1.2);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showTranscript, setShowTranscript] = useState(!!transcript);
  const [showSummary, setShowSummary] = useState(!!summary);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [currentSearchIndex, setCurrentSearchIndex] = useState(-1);
  const containerRef = useRef(null);
  const pdfDocRef = useRef(null);
  const pageRefs = useRef({});

  const loadPdf = useCallback(async () => {
    if (!src) return;
    setLoading(true);
    setError(null);
    try {
      const pdfjsLib = await import('pdfjs-dist');
      pdfjsLib.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.js`;
      const loadingTask = pdfjsLib.getDocument(src);
      const pdf = await loadingTask.promise;
      pdfDocRef.current = pdf;
      setNumPages(pdf.numPages);
      setPageNumber(1);
      setLoading(false);
    } catch (err) {
      setError('Failed to load PDF. The file may be corrupted or inaccessible.');
      setLoading(false);
    }
  }, [src]);

  useEffect(() => {
    loadPdf();
  }, [loadPdf]);

  const renderPage = useCallback(async (pageNum) => {
    if (!pdfDocRef.current || pageNum < 1 || pageNum > numPages) return;
    const page = await pdfDocRef.current.getPage(pageNum);
    const viewport = page.getViewport({ scale });
    const canvas = pageRefs.current[pageNum];
    if (!canvas) return;
    const context = canvas.getContext('2d');
    canvas.height = viewport.height;
    canvas.width = viewport.width;
    await page.render({ canvasContext: context, viewport }).promise;
  }, [numPages, scale]);

  useEffect(() => {
    if (pageNumber && !loading) renderPage(pageNumber);
  }, [pageNumber, scale, loading, renderPage]);

  const goToPage = (newPage) => {
    const clamped = Math.max(1, Math.min(newPage, numPages || 1));
    setPageNumber(clamped);
    onPageChange?.(clamped);
  };

  const handleSearch = async () => {
    if (!pdfDocRef.current || !searchQuery.trim()) {
      setSearchResults([]);
      return;
    }
    const results = [];
    for (let i = 1; i <= numPages; i++) {
      const page = await pdfDocRef.current.getPage(i);
      const textContent = await page.getTextContent();
      const text = textContent.items.map(item => item.str).join(' ');
      const regex = new RegExp(searchQuery, 'gi');
      let match;
      while ((match = regex.exec(text)) !== null) {
        results.push({ page: i, index: match.index, context: text.slice(Math.max(0, match.index - 50), match.index + 100) });
      }
    }
    setSearchResults(results);
    setCurrentSearchIndex(results.length ? 0 : -1);
    if (results.length) goToPage(results[0].page);
  };

  useEffect(() => {
    const timer = setTimeout(handleSearch, 300);
    return () => clearTimeout(timer);
  }, [searchQuery, numPages]);

  const nextSearchResult = () => setCurrentSearchIndex(i => (i + 1) % searchResults.length);
  const prevSearchResult = () => setCurrentSearchIndex(i => (i - 1 + searchResults.length) % searchResults.length);

  if (!src) return <div className="pdf-viewer empty">No PDF source provided</div>;
  if (loading) return <div className="pdf-viewer loading" role="status">Loading PDF…</div>;
  if (error) return <div className="pdf-viewer error" role="alert">{error}</div>;

  return (
    <div className={`pdf-viewer ${className}`}>
      <div className="pdf-toolbar">
        <div className="pdf-toolbar-left">
          <button className="icon-button" onClick={() => goToPage(pageNumber - 1)} disabled={pageNumber <= 1} aria-label="Previous page"><ChevronLeft size={18} /></button>
          <button className="icon-button" onClick={() => goToPage(pageNumber + 1)} disabled={pageNumber >= numPages} aria-label="Next page"><ChevronRight size={18} /></button>
          <span className="page-indicator" aria-live="polite">Page {pageNumber} of {numPages}</span>
          <div className="zoom-control">
            <button className="icon-button" onClick={() => setScale(s => Math.max(0.5, s - 0.2))} aria-label="Zoom out"><RotateCcw size={16} /></button>
            <span>{Math.round(scale * 100)}%</span>
            <button className="icon-button" onClick={() => setScale(s => Math.min(3, s + 0.2))} aria-label="Zoom in"><RotateCcw size={16} style={{ transform: 'rotate(180deg)' }} /></button>
          </div>
        </div>
        <div className="pdf-toolbar-center">
          <div className="search-box">
            <Search size={16} />
            <input type="text" placeholder="Search in document…" value={searchQuery} onChange={e => setSearchQuery(e.target.value)} aria-label="Search in PDF" />
            {searchResults.length && (
              <>
                <button className="icon-button" onClick={prevSearchResult} aria-label="Previous result"><ChevronLeft size={14} /></button>
                <span className="search-count">{currentSearchIndex + 1} / {searchResults.length}</span>
                <button className="icon-button" onClick={nextSearchResult} aria-label="Next result"><ChevronRight size={14} /></button>
              </>
            )}
          </div>
        </div>
        <div className="pdf-toolbar-right">
          <button className="icon-button" onClick={() => setShowTranscript(!showTranscript)} aria-label={showTranscript ? 'Hide transcript' : 'Show transcript'} aria-pressed={showTranscript}><FileText size={18} /></button>
          <button className="icon-button" onClick={() => setShowSummary(!showSummary)} aria-label={showSummary ? 'Hide summary' : 'Show summary'} aria-pressed={showSummary}><Sparkles size={18} /></button>
          <a href={src} download className="icon-button" aria-label="Download PDF"><Download size={18} /></a>
          <button className="icon-button" onClick={() => containerRef.current?.requestFullscreen()} aria-label="Fullscreen"><Maximize2 size={18} /></button>
        </div>
      </div>

      <div className="pdf-main" ref={containerRef}>
        <div className="pdf-canvas-wrapper">
          <canvas ref={el => pageRefs.current[pageNumber] = el} className="pdf-canvas" aria-label={`Page ${pageNumber} of PDF`} />
        </div>

        {((showTranscript && transcript) || (showSummary && summary)) && (
          <aside className="pdf-sidebar" aria-label="Document insights">
            {showTranscript && transcript && (
              <TranscriptPanel transcript={transcript} onSelect={onTranscriptSelect} activePage={pageNumber} searchQuery={searchQuery} />
            )}
            {showSummary && summary && (
              <SummaryPanel summary={summary} />
            )}
          </aside>
        )}
      </div>
    </div>
  );
}

function TranscriptPanel({ transcript, onSelect, activePage, searchQuery }) {
  const [segments, setSegments] = useState([]);
  useEffect(() => {
    if (!transcript) return;
    const parsed = typeof transcript === 'string' ? transcript.split('\n').filter(Boolean).map((line, i) => ({ text: line, timestamp: i * 30 })) : transcript;
    setSegments(parsed);
  }, [transcript]);

  const filtered = segments.filter(s => !searchQuery || s.text.toLowerCase().includes(searchQuery.toLowerCase()));

  return (
    <div className="transcript-panel">
      <h3>Transcript</h3>
      <div className="transcript-segments" role="list">
        {filtered.map((segment, i) => (
          <button
            key={i}
            className={`transcript-segment ${Math.floor(segment.timestamp / 60) === activePage ? 'active' : ''}`}
            onClick={() => onSelect?.(segment)}
            role="listitem"
          >
            <span className="segment-time">{formatTime(segment.timestamp)}</span>
            <span className="segment-text">{segment.text}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

function SummaryPanel({ summary }) {
  return (
    <div className="summary-panel">
      <h3>AI Summary</h3>
      <div className="summary-content">
        {typeof summary === 'string' ? summary.split('\n').map((line, i) => <p key={i}>{line}</p>) : <pre>{JSON.stringify(summary, null, 2)}</pre>}
      </div>
    </div>
  );
}

function formatTime(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

export default PDFViewer;