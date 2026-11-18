import { useState, useMemo, useRef, useEffect } from 'react';
import { 
  FileDown, 
  Printer, 
  FileText, 
  Table, 
  Code, 
  Check, 
  Copy, 
  Clock, 
  BookOpen, 
  GraduationCap,
  Sparkles
} from 'lucide-react';
import { fetchQuestions, fetchStudyGuide } from '../../services/api';
import { useExportActions, useRequestGuard } from '../../hooks';
import { Modal } from '../common';
import { formatExamTime } from '../../utils';
import { pickExportQuestions } from '../../utils/questionHelpers';
import ExportPaperPreview from './ExportPaperPreview';
import ExportScopeSelector from './ExportScopeSelector';
import ExportDataFormatPane from './ExportDataFormatPane';
import StudyGuideExportPane from './StudyGuideExportPane';
import { EMPTY_ARRAY, QUESTION_STATUS } from '../../constants';

const CODE_FORMATS = {
  csv: {
    callout:
      'Exports a clean spreadsheet containing question stems, passages, choices A-D, correct answers, explanations, and quality scores for Excel or Google Sheets.',
    downloadLabel: 'Download CSV Table',
    downloadId: 'btn-download-csv'
  },
  json: {
    callout:
      'Exports full structured question data including passages, choices, explanations, and quality evaluation in JSON format.',
    downloadLabel: 'Download JSON File',
    downloadId: 'btn-download-json'
  }
};

export default function ExportPrintModal({
  isOpen,
  onClose,
  allQuestions = EMPTY_ARRAY,
  selectedIds = EMPTY_ARRAY,
  filteredQuestions = EMPTY_ARRAY,
  hasActiveFilters = false,
  bankTotalCount = 0,
  onShowToast
}) {
  // Determine initial scope: selected > filtered > all
  const initialScope = selectedIds.length > 0 
    ? 'selected' 
    : (hasActiveFilters && filteredQuestions.length > 0 ? 'filtered' : 'all');

  const [scope, setScope] = useState(initialScope);
  const [format, setFormat] = useState('paper'); // 'paper' | 'csv' | 'json' | 'study_guide'
  const [paperMode, setPaperMode] = useState('student'); // 'student' | 'studypack'
  const [fetchedAll, setFetchedAll] = useState(null);
  const [studyGuide, setStudyGuide] = useState(null);
  const [isSynthesizingGuide, setIsSynthesizingGuide] = useState(false);
  const [guideCopied, setGuideCopied] = useState(false);
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
  // The list in hand is already filtered server-side; the bank total comes from the API until
  // the whole bank has been fetched for the export itself
  const allCount = fetchedAll ? fetchedAll.length : bankTotalCount || allQuestions.length;

  const exportQuestions = useMemo(
    () =>
      pickExportQuestions({ scope, selectedIds, bankPool, filteredQuestions, hasActiveFilters }),
    [scope, selectedIds, bankPool, filteredQuestions, hasActiveFilters]
  );

  const timeAllowed = useMemo(() => formatExamTime(exportQuestions), [exportQuestions]);

  const handleSynthesizeGuide = async () => {
    if (isSynthesizingGuide || exportQuestions.length === 0) return;
    setIsSynthesizingGuide(true);
    try {
      const data = await fetchStudyGuide(exportQuestions);
      setStudyGuide(data);
    } catch (err) {
      onShowToast?.({
        type: 'danger',
        title: 'Study Guide Error',
        message: err.message || 'Failed to synthesize study guide.'
      });
    } finally {
      setIsSynthesizingGuide(false);
    }
  };

  const handleCopyGuide = async () => {
    if (!studyGuide?.markdown_guide) return;
    try {
      await navigator.clipboard.writeText(studyGuide.markdown_guide);
      setGuideCopied(true);
      setTimeout(() => setGuideCopied(false), 2000);
      onShowToast?.({
        type: 'success',
        title: 'Copied to Clipboard',
        message: 'High-Yield Study Guide copied as Markdown.'
      });
    } catch (err) {
      console.error('Clipboard copy failed:', err);
    }
  };

  const handleDownloadGuide = () => {
    if (!studyGuide?.markdown_guide) return;
    const blob = new Blob([studyGuide.markdown_guide], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `MCAT_Study_Guide_${exportQuestions.length}Qs.md`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const { formats, printPaper } = useExportActions({ questions: exportQuestions, paperMode, onShowToast });
  const isCodeFormat = format === 'csv' || format === 'json';
  const codeFormat = isCodeFormat ? formats[format] : null;
  const codeMeta = isCodeFormat ? CODE_FORMATS[format] : null;

  const footer = (
    <>
      <div className="exam-export-footer-info">
        Ready to export <strong>{exportQuestions.length}</strong> question{exportQuestions.length === 1 ? '' : 's'}
      </div>

      <div className="exam-export-actions">
        <button type="button" className="btn-ghost" onClick={onClose}>
          Cancel
        </button>

        {format === 'paper' && (
          <button
            type="button"
            className="btn-primary"
            id="btn-trigger-print-paper"
            onClick={printPaper}
            disabled={exportQuestions.length === 0}
          >
            <Printer size={14} />
            <span>Print / Save as PDF</span>
          </button>
        )}

        {format === 'study_guide' && (
          <>
            <button
              type="button"
              className="btn-secondary"
              onClick={handleCopyGuide}
              disabled={!studyGuide?.markdown_guide}
            >
              {guideCopied ? <Check size={14} color="var(--status-success)" /> : <Copy size={14} />}
              <span>{guideCopied ? 'Copied' : 'Copy Guide Markdown'}</span>
            </button>
            <button
              type="button"
              className="btn-primary"
              onClick={handleDownloadGuide}
              disabled={!studyGuide?.markdown_guide}
            >
              <FileDown size={14} />
              <span>Download Guide (.md)</span>
            </button>
          </>
        )}

        {isCodeFormat && codeFormat && codeMeta && (
          <>
            <button type="button" className="btn-secondary" onClick={codeFormat.copy}>
              {codeFormat.copied ? <Check size={14} color="var(--status-success)" /> : <Copy size={14} />}
              <span>{codeFormat.copied ? 'Copied' : `Copy ${codeFormat.label}`}</span>
            </button>
            <button
              type="button"
              className="btn-primary"
              id={codeMeta.downloadId}
              onClick={codeFormat.download}
              disabled={exportQuestions.length === 0}
            >
              <FileDown size={14} />
              <span>{codeMeta.downloadLabel}</span>
            </button>
          </>
        )}
      </div>
    </>
  );

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Export & Print Exam"
      icon={<FileDown size={18} />}
      maxWidth="960px"
      className="exam-export-modal"
      bodyClassName="exam-export-body"
      footerClassName="exam-export-footer"
      footer={footer}
    >
          {/* Top Scope & Format Bar */}
          <div className="exam-export-topbar">
            {/* Scope Selection */}
            <ExportScopeSelector
              scope={scope}
              onScopeChange={setScope}
              exportCount={exportQuestions.length}
              selectedCount={selectedIds.length}
              filteredCount={filteredQuestions.length}
              allCount={allCount}
              hasActiveFilters={hasActiveFilters}
            />

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
                <button
                  type="button"
                  className={`pill-track-btn ${format === 'study_guide' ? 'active' : ''}`}
                  onClick={() => setFormat('study_guide')}
                >
                  <Sparkles size={13} color="var(--brand-primary)" />
                  <span>AI Study Guide</span>
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

          {/* TAB 2/3: CSV or JSON code preview */}
          {codeFormat && codeMeta && (
            <ExportDataFormatPane
              callout={codeMeta.callout}
              content={codeFormat.content}
            />
          )}

          {/* TAB 4: AI High-Yield Study Guide */}
          {format === 'study_guide' && (
            <StudyGuideExportPane
              studyGuide={studyGuide}
              isSynthesizingGuide={isSynthesizingGuide}
              exportQuestions={exportQuestions}
              handleSynthesizeGuide={handleSynthesizeGuide}
            />
          )}
    </Modal>
  );
}
