import { useState, useMemo, useRef, useEffect } from 'react';
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
import { useFocusTrap, useExportActions, useRequestGuard } from '../../hooks';
import { formatExamTime } from '../../utils';
import { pickExportQuestions } from '../../utils/questionHelpers';
import ExportPaperPreview from './ExportPaperPreview';
import { EMPTY_ARRAY, QUESTION_STATUS } from '../../constants';

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
  const [fetchedAll, setFetchedAll] = useState(null);
  const previewRef = useRef(null);

  const guard = useRequestGuard();
  useEffect(() => {
    if (!hasActiveFilters) return;
    // With filters on, the "all" scope needs the whole bank; only the newest request may
    // write state, and the guard retires it when the dialog unmounts
    const request = guard.begin();
    fetchQuestions({ status: QUESTION_STATUS.IN_BANK }, request.signal)
      .then((res) => {
        if (request.isCurrent() && res?.questions) setFetchedAll(res.questions);
      })
      .catch(() => {});
  }, [guard, hasActiveFilters]);

  // Compute active export dataset
  const bankPool = fetchedAll || allQuestions;

  const exportQuestions = useMemo(
    () =>
      pickExportQuestions({ scope, selectedIds, bankPool, filteredQuestions, hasActiveFilters }),
    [scope, selectedIds, bankPool, filteredQuestions, hasActiveFilters]
  );

  const timeAllowed = useMemo(() => formatExamTime(exportQuestions), [exportQuestions]);

  const {
    csvContent,
    jsonContent,
    copiedCsv,
    copiedJson,
    handleDownloadCsv,
    handleCopyCsv,
    handleDownloadJson,
    handleCopyJson,
    handleNativePrint
  } = useExportActions({ questions: exportQuestions, paperMode, onShowToast });

  if (!isOpen) return null;

  return (
    <div className="modal-backdrop-theme" onClick={onClose}>
      <div 
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="export-modal-title"
        className="modal-card modal-card-theme exam-export-modal" 
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="modal-header">
          <div className="modal-title-group">
            <div className="modal-icon-badge exam-export-icon-badge">
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
        <div className="modal-body exam-export-body">
          
          {/* Top Scope & Format Bar */}
          <div className="exam-export-topbar">
            {/* Scope Selection */}
            <div className="exam-export-group">
              <span className="exam-export-group-label">
                Questions ({exportQuestions.length})
              </span>
              <div className="pill-track">
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
            <div className="exam-export-group">
              <span className="exam-export-group-label">
                Format
              </span>
              <div className="pill-track">
                <button
                  type="button"
                  className={`pill-track-btn ${format === 'paper' ? 'active' : ''}`}
                  onClick={() => setFormat('paper')}
                >
                  <FileText size={13} />
                  <span>Printable Exam</span>
                </button>
                <button
                  type="button"
                  className={`pill-track-btn ${format === 'csv' ? 'active' : ''}`}
                  onClick={() => setFormat('csv')}
                >
                  <Table size={13} />
                  <span>CSV</span>
                </button>
                <button
                  type="button"
                  className={`pill-track-btn ${format === 'json' ? 'active' : ''}`}
                  onClick={() => setFormat('json')}
                >
                  <Code size={13} />
                  <span>JSON</span>
                </button>
              </div>
            </div>
          </div>

          {/* TAB 1: PRINTABLE EXAM PAPER */}
          {format === 'paper' && (
            <div className="exam-export-tab-pane">
              {/* Paper Controls Strip */}
              <div className="exam-export-paper-controls">
                <div className="exam-export-paper-mode-group">
                  <span className="exam-export-paper-mode-label">Paper Type:</span>
                  <div className="pill-track">
                    <button
                      type="button"
                      className={`pill-track-btn ${paperMode === 'student' ? 'active' : ''}`}
                      onClick={() => setPaperMode('student')}
                    >
                      <GraduationCap size={13} />
                      <span>Student Test</span>
                    </button>
                    <button
                      type="button"
                      className={`pill-track-btn ${paperMode === 'studypack' ? 'active' : ''}`}
                      onClick={() => setPaperMode('studypack')}
                    >
                      <BookOpen size={13} />
                      <span>Full Study Pack</span>
                    </button>
                  </div>
                </div>

                <div className="exam-export-paper-meta">
                  <span className="exam-export-paper-meta-badge">
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
            <div className="exam-export-tab-pane">
              <div className="exam-export-callout">
                Exports a clean spreadsheet containing question stems, passages, choices A-D, correct answers, explanations, and quality scores for Excel or Google Sheets.
              </div>

              <div className="exam-export-code-preview">
                {csvContent}
              </div>
            </div>
          )}

          {/* TAB 3: JSON DATASET */}
          {format === 'json' && (
            <div className="exam-export-tab-pane">
              <div className="exam-export-callout">
                Exports full structured question data including passages, choices, explanations, and quality evaluation in JSON format.
              </div>

              <div className="exam-export-code-preview">
                {jsonContent}
              </div>
            </div>
          )}

        </div>

        {/* Modal Footer */}
        <div className="modal-footer exam-export-footer">
          <div className="exam-export-footer-info">
            Ready to export <strong>{exportQuestions.length}</strong> question{exportQuestions.length === 1 ? '' : 's'}
          </div>

          <div className="exam-export-actions">
            <button
              type="button"
              className="btn-ghost"
              onClick={onClose}
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
