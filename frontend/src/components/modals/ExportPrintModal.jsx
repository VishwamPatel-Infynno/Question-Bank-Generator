import React, { useState, useMemo, useRef, useEffect } from 'react';
import { 
  FileDown, 
  Printer, 
  FileText, 
  Table, 
  Code, 
  Check, 
  Copy, 
  X, 
  Clock, 
  BookOpen, 
  GraduationCap
} from 'lucide-react';
import { fetchQuestions } from '../../services/api';
import { useFocusTrap } from '../../hooks';
import { 
  formatExamTime,
  generateExamCsv,
  generateExamJson,
  generateExamHtmlDoc 
} from '../../utils';
import ExportPaperPreview from './ExportPaperPreview';

const EMPTY_ARRAY = [];


export default function ExportPrintModal({
  isOpen,
  onClose,
  allQuestions = EMPTY_ARRAY,
  selectedIds = EMPTY_ARRAY,
  filteredQuestions = EMPTY_ARRAY,
  hasActiveFilters = false,
  onShowToast
}) {
  const modalRef = useFocusTrap({ isActive: Boolean(isOpen), onClose });

  // Determine initial scope: selected > filtered > all
  const initialScope = selectedIds.length > 0 
    ? 'selected' 
    : (hasActiveFilters && filteredQuestions.length > 0 ? 'filtered' : 'all');

  const [scope, setScope] = useState(initialScope);
  const [format, setFormat] = useState('paper'); // 'paper' | 'csv' | 'json'
  const [paperMode, setPaperMode] = useState('student'); // 'student' | 'studypack'
  const [copiedJson, setCopiedJson] = useState(false);
  const [copiedCsv, setCopiedCsv] = useState(false);
  const [fetchedAll, setFetchedAll] = useState(null);
  const previewRef = useRef(null);

  useEffect(() => {
    if (hasActiveFilters) {
      fetchQuestions({ status: 'in_bank' }).then(res => {
        if (res?.questions) setFetchedAll(res.questions);
      }).catch(() => {});
    }
  }, [hasActiveFilters]);

  // Compute active export dataset
  const bankPool = fetchedAll || allQuestions;

  const exportQuestions = useMemo(() => {
    if (scope === 'selected' && selectedIds.length > 0) {
      return bankPool.filter(q => selectedIds.includes(q.id));
    }
    if (scope === 'filtered' && hasActiveFilters) {
      return filteredQuestions;
    }
    return bankPool;
  }, [scope, selectedIds, bankPool, filteredQuestions, hasActiveFilters]);

  const timeAllowed = useMemo(() => formatExamTime(exportQuestions), [exportQuestions]);

  // Generate CSV String
  const csvContent = useMemo(() => {
    return generateExamCsv(exportQuestions);
  }, [exportQuestions]);

  // Download CSV
  const handleDownloadCsv = () => {
    if (!csvContent) return;
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `mcat_exam_${exportQuestions.length}_questions.csv`;
    a.click();
    URL.revokeObjectURL(url);
    if (onShowToast) {
      onShowToast({
        type: 'success',
        title: 'CSV Exported',
        message: `Successfully downloaded CSV for ${exportQuestions.length} questions.`
      });
    }
  };

  // Copy CSV
  const handleCopyCsv = async () => {
    if (!csvContent) return;
    try {
      await navigator.clipboard.writeText(csvContent);
      setCopiedCsv(true);
      setTimeout(() => setCopiedCsv(false), 2000);
      if (onShowToast) {
        onShowToast({
          type: 'success',
          title: 'Copied to Clipboard',
          message: 'CSV data copied.'
        });
      }
    } catch {
      // Fallback
    }
  };

  // Generate JSON String
  const jsonContent = useMemo(() => {
    return generateExamJson(exportQuestions);
  }, [exportQuestions]);

  // Download JSON
  const handleDownloadJson = () => {
    const blob = new Blob([jsonContent], { type: 'application/json;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `mcat_exam_${exportQuestions.length}_questions.json`;
    a.click();
    URL.revokeObjectURL(url);
    if (onShowToast) {
      onShowToast({
        type: 'success',
        title: 'JSON Exported',
        message: `Successfully downloaded JSON for ${exportQuestions.length} questions.`
      });
    }
  };

  // Copy JSON
  const handleCopyJson = async () => {
    try {
      await navigator.clipboard.writeText(jsonContent);
      setCopiedJson(true);
      setTimeout(() => setCopiedJson(false), 2000);
      if (onShowToast) {
        onShowToast({
          type: 'success',
          title: 'Copied to Clipboard',
          message: 'JSON data copied.'
        });
      }
    } catch {
      // Fallback
    }
  };

  // Trigger Native Print / Save as PDF
  const handleNativePrint = () => {
    if (!exportQuestions || exportQuestions.length === 0) return;

    const printWindow = window.open('', '_blank');
    if (!printWindow) {
      if (onShowToast) {
        onShowToast({
          type: 'error',
          title: 'Pop-up Blocked',
          message: 'Please allow pop-ups for this site to print or save as PDF.'
        });
      }
      return;
    }

    const htmlDoc = generateExamHtmlDoc(exportQuestions, { paperMode });
    printWindow.document.open();
    printWindow.document.write(htmlDoc);
    printWindow.document.close();
  };

  if (!isOpen) return null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div 
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="export-modal-title"
        className="modal-card" 
        onClick={(e) => e.stopPropagation()}
        style={{ maxWidth: '960px', width: '95vw', maxHeight: '90vh', display: 'flex', flexDirection: 'column' }}
      >
        {/* Modal Header */}
        <div className="modal-header">
          <div className="modal-title-group">
            <div className="modal-icon-badge" style={{ color: 'var(--brand-primary)', background: 'var(--brand-light)' }}>
              <FileDown size={18} />
            </div>
            <div>
              <h2 id="export-modal-title" className="modal-title">Export &amp; Print Exam</h2>
            </div>
          </div>
          <button 
            type="button" 
            className="modal-close-btn" 
            onClick={onClose}
            aria-label="Close Export &amp; Print"
          >
            <X size={18} />
          </button>
        </div>

        {/* Modal Body */}
        <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '16px', overflowY: 'auto' }}>
          
          {/* Top Scope & Format Bar */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '16px', justifyContent: 'space-between', alignItems: 'center', background: 'var(--bg-surface-elevated)', padding: '12px 16px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
            {/* Scope Selection */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <span style={{ fontSize: '0.72rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)' }}>
                Questions ({exportQuestions.length})
              </span>
              <div className="pill-track" style={{ background: 'var(--bg-surface)' }}>
                {selectedIds.length > 0 && (
                  <button
                    type="button"
                    className={`pill-track-btn ${scope === 'selected' ? 'active' : ''}`}
                    onClick={() => setScope('selected')}
                  >
                    <span>Selected ({selectedIds.length})</span>
                  </button>
                )}
                {hasActiveFilters && (
                  <button
                    type="button"
                    className={`pill-track-btn ${scope === 'filtered' ? 'active' : ''}`}
                    onClick={() => setScope('filtered')}
                  >
                    <span>Filtered ({filteredQuestions.length})</span>
                  </button>
                )}
                <button
                  type="button"
                  className={`pill-track-btn ${scope === 'all' ? 'active' : ''}`}
                  onClick={() => setScope('all')}
                >
                  <span>All ({allQuestions.length})</span>
                </button>
              </div>
            </div>

            {/* Format Selection */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <span style={{ fontSize: '0.72rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)' }}>
                Format
              </span>
              <div className="pill-track" style={{ background: 'var(--bg-surface)' }}>
                <button
                  type="button"
                  className={`pill-track-btn ${format === 'paper' ? 'active' : ''}`}
                  onClick={() => setFormat('paper')}
                  style={{ gap: '6px' }}
                >
                  <FileText size={13} />
                  <span>Printable Exam</span>
                </button>
                <button
                  type="button"
                  className={`pill-track-btn ${format === 'csv' ? 'active' : ''}`}
                  onClick={() => setFormat('csv')}
                  style={{ gap: '6px' }}
                >
                  <Table size={13} />
                  <span>CSV</span>
                </button>
                <button
                  type="button"
                  className={`pill-track-btn ${format === 'json' ? 'active' : ''}`}
                  onClick={() => setFormat('json')}
                  style={{ gap: '6px' }}
                >
                  <Code size={13} />
                  <span>JSON</span>
                </button>
              </div>
            </div>
          </div>

          {/* TAB 1: PRINTABLE EXAM PAPER */}
          {format === 'paper' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              {/* Paper Controls Strip */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px', padding: '10px 14px', background: 'var(--bg-surface-subtle)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-primary)' }}>Paper Type:</span>
                  <div className="pill-track">
                    <button
                      type="button"
                      className={`pill-track-btn ${paperMode === 'student' ? 'active' : ''}`}
                      onClick={() => setPaperMode('student')}
                      style={{ gap: '6px', fontSize: '0.78rem' }}
                    >
                      <GraduationCap size={13} />
                      <span>Student Test</span>
                    </button>
                    <button
                      type="button"
                      className={`pill-track-btn ${paperMode === 'studypack' ? 'active' : ''}`}
                      onClick={() => setPaperMode('studypack')}
                      style={{ gap: '6px', fontSize: '0.78rem' }}
                    >
                      <BookOpen size={13} />
                      <span>Full Study Pack</span>
                    </button>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '14px', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <Clock size={13} color="var(--brand-primary)" /> Estimated Time: <strong>{timeAllowed}</strong>
                  </span>
                  <span>&bull;</span>
                  <span><strong>{exportQuestions.length}</strong> Questions</span>
                </div>
              </div>

              {/* Live Document Preview Card */}
              <ExportPaperPreview
                previewRef={previewRef}
                paperMode={paperMode}
                exportQuestions={exportQuestions}
                timeAllowed={timeAllowed}
              />
            </div>
          )}

          {/* TAB 2: CSV SPREADSHEET */}
          {format === 'csv' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ padding: '10px 14px', background: 'var(--bg-surface-subtle)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                Exports a clean spreadsheet containing question stems, passages, choices A-D, correct answers, explanations, and quality scores for Excel or Google Sheets.
              </div>

              <div 
                style={{
                  background: 'var(--bg-app)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '12px 14px',
                  fontFamily: 'var(--font-mono)',
                  fontSize: '0.72rem',
                  color: 'var(--text-secondary)',
                  maxHeight: '340px',
                  overflowY: 'auto',
                  whiteSpace: 'pre-wrap',
                  lineHeight: 1.5
                }}
              >
                {csvContent}
              </div>
            </div>
          )}

          {/* TAB 3: JSON DATASET */}
          {format === 'json' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ padding: '10px 14px', background: 'var(--bg-surface-subtle)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                Exports full structured question data including passages, choices, explanations, and quality evaluation in JSON format.
              </div>

              <div 
                style={{
                  background: 'var(--bg-app)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '12px 14px',
                  fontFamily: 'var(--font-mono)',
                  fontSize: '0.72rem',
                  color: 'var(--text-secondary)',
                  maxHeight: '340px',
                  overflowY: 'auto',
                  whiteSpace: 'pre-wrap',
                  lineHeight: 1.5
                }}
              >
                {jsonContent}
              </div>
            </div>
          )}

        </div>

        {/* Modal Footer */}
        <div className="modal-footer" style={{ justifyContent: 'space-between' }}>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            Ready to export <strong>{exportQuestions.length}</strong> question{exportQuestions.length === 1 ? '' : 's'}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button
              type="button"
              className="btn-ghost"
              onClick={onClose}
              style={{ padding: '7px 14px', fontSize: '0.8rem' }}
            >
              Cancel
            </button>

            {format === 'paper' && (
              <button
                type="button"
                className="btn-primary"
                id="btn-trigger-print-paper"
                onClick={handleNativePrint}
                disabled={exportQuestions.length === 0}
                style={{ padding: '7px 16px', fontSize: '0.8rem', gap: '6px' }}
              >
                <Printer size={14} />
                <span>Print / Save as PDF</span>
              </button>
            )}

            {format === 'csv' && (
              <>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={handleCopyCsv}
                  style={{ padding: '7px 14px', fontSize: '0.8rem', gap: '6px' }}
                >
                  {copiedCsv ? <Check size={14} color="var(--status-success)" /> : <Copy size={14} />}
                  <span>{copiedCsv ? 'Copied' : 'Copy CSV'}</span>
                </button>
                <button
                  type="button"
                  className="btn-primary"
                  id="btn-download-csv"
                  onClick={handleDownloadCsv}
                  disabled={exportQuestions.length === 0}
                  style={{ padding: '7px 16px', fontSize: '0.8rem', gap: '6px' }}
                >
                  <FileDown size={14} />
                  <span>Download CSV Table</span>
                </button>
              </>
            )}

            {format === 'json' && (
              <>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={handleCopyJson}
                  style={{ padding: '7px 14px', fontSize: '0.8rem', gap: '6px' }}
                >
                  {copiedJson ? <Check size={14} color="var(--status-success)" /> : <Copy size={14} />}
                  <span>{copiedJson ? 'Copied' : 'Copy JSON'}</span>
                </button>
                <button
                  type="button"
                  className="btn-primary"
                  id="btn-download-json"
                  onClick={handleDownloadJson}
                  disabled={exportQuestions.length === 0}
                  style={{ padding: '7px 16px', fontSize: '0.8rem', gap: '6px' }}
                >
                  <FileDown size={14} />
                  <span>Download JSON File</span>
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
