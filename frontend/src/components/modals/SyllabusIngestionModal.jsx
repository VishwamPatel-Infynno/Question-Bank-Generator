import { useState, useRef } from 'react';
import {
  FileText,
  UploadCloud,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  FileCode,
  X,
  Layers,
  ArrowRight,
  BookOpen
} from 'lucide-react';
import { Modal } from '../common';
import { ingestSyllabusFile, ingestSyllabusText } from '../../services/api';

/**
 * SyllabusIngestionModal
 *
 * AI-native document ingestion modal allowing educators to upload syllabi,
 * lecture outlines, or exam study guides (PDF, TXT, MD) or paste text,
 * automatically mapping curriculum content to AAMC MCAT taxonomy.
 */
export default function SyllabusIngestionModal({
  isOpen,
  onClose,
  onApply
}) {
  const [activeTab, setActiveTab] = useState('file'); // 'file' | 'text'
  const [selectedFile, setSelectedFile] = useState(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [textContent, setTextContent] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState(null);
  const [analysisResult, setAnalysisResult] = useState(null);
  const fileInputRef = useRef(null);

  const handleFileDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      setSelectedFile(file);
      setError(null);
      setAnalysisResult(null);
    }
  };

  const handleFileSelect = (e) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      setError(null);
      setAnalysisResult(null);
    }
  };

  const handleClearFile = () => {
    setSelectedFile(null);
    setAnalysisResult(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleAnalyze = async () => {
    setError(null);
    setIsAnalyzing(true);
    try {
      let data;
      if (activeTab === 'file') {
        if (!selectedFile) {
          setError('Please select or drop a syllabus document first.');
          setIsAnalyzing(false);
          return;
        }
        data = await ingestSyllabusFile(selectedFile);
      } else {
        if (!textContent.trim() || textContent.trim().length < 10) {
          setError('Please enter at least 10 characters of syllabus text.');
          setIsAnalyzing(false);
          return;
        }
        data = await ingestSyllabusText({ content: textContent.trim(), title: 'Pasted Syllabus' });
      }
      setAnalysisResult(data);
    } catch (err) {
      console.error('Syllabus ingestion failed:', err);
      setError(err.message || 'Failed to analyze syllabus. Please check format.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleApplyToWizard = () => {
    if (!analysisResult) return;
    if (onApply) {
      onApply(analysisResult);
    }
    onClose();
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return '';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const modalIcon = (
    <div className="syllabus-modal-icon-wrap">
      <FileText size={18} />
    </div>
  );

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="AI Document & Syllabus Ingestion"
      subtitle="Map course syllabi, lecture notes, or study guides (PDF, TXT, MD) to the official AAMC MCAT outline."
      icon={modalIcon}
      maxWidth="680px"
      isProcessing={isAnalyzing}
    >
      <div className="syllabus-modal-body">
        {/* Tab Selection */}
        <div className="syllabus-modal-tabs" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'file'}
            className={`syllabus-tab-btn ${activeTab === 'file' ? 'active' : ''}`}
            onClick={() => setActiveTab('file')}
            disabled={isAnalyzing}
          >
            <UploadCloud size={14} />
            <span>Upload Document (PDF, TXT, MD)</span>
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'text'}
            className={`syllabus-tab-btn ${activeTab === 'text' ? 'active' : ''}`}
            onClick={() => setActiveTab('text')}
            disabled={isAnalyzing}
          >
            <FileCode size={14} />
            <span>Paste Syllabus Text</span>
          </button>
        </div>

        {error && (
          <div className="syllabus-error-banner" role="alert">
            <AlertCircle size={15} />
            <span>{error}</span>
          </div>
        )}

        {/* File Upload Mode */}
        {activeTab === 'file' && (
          <div className="syllabus-tab-content">
            {!selectedFile ? (
              <div
                className={`syllabus-dropzone ${isDragOver ? 'syllabus-dropzone-dragover' : ''}`}
                onDragOver={(e) => {
                  e.preventDefault();
                  setIsDragOver(true);
                }}
                onDragLeave={() => setIsDragOver(false)}
                onDrop={handleFileDrop}
                onClick={() => fileInputRef.current?.click()}
                tabIndex={0}
                role="button"
                aria-label="Upload syllabus file"
              >
                <input
                  type="file"
                  ref={fileInputRef}
                  style={{ display: 'none' }}
                  accept=".pdf,.txt,.md,.json,.csv"
                  onChange={handleFileSelect}
                />
                <div className="syllabus-dropzone-inner">
                  <div className="syllabus-dropzone-icon">
                    <UploadCloud size={32} />
                  </div>
                  <div className="syllabus-dropzone-title">
                    Drop syllabus or lecture notes here
                  </div>
                  <div className="syllabus-dropzone-hint">
                    Supports <strong>PDF</strong>, <strong>TXT</strong>, or <strong>Markdown</strong> (up to 20 MB)
                  </div>
                  <button type="button" className="btn-secondary syllabus-browse-btn">
                    Browse Files
                  </button>
                </div>
              </div>
            ) : (
              <div className="syllabus-file-preview-card">
                <div className="syllabus-file-info">
                  <div className="syllabus-file-icon">
                    <FileText size={20} />
                  </div>
                  <div className="syllabus-file-meta">
                    <div className="syllabus-file-name">{selectedFile.name}</div>
                    <div className="syllabus-file-size">{formatFileSize(selectedFile.size)}</div>
                  </div>
                </div>
                <button
                  type="button"
                  className="syllabus-file-remove-btn"
                  onClick={handleClearFile}
                  title="Remove file"
                  aria-label="Remove selected file"
                  disabled={isAnalyzing}
                >
                  <X size={15} />
                </button>
              </div>
            )}
          </div>
        )}

        {/* Paste Text Mode */}
        {activeTab === 'text' && (
          <div className="syllabus-tab-content">
            <textarea
              className="syllabus-textarea"
              rows={7}
              placeholder="Paste course syllabus, lecture outline, textbook table of contents, or learning objectives here (e.g. 'Week 4: Enzyme kinetics, Michaelis-Menten derivation, competitive inhibition, allosteric regulation...')"
              value={textContent}
              onChange={(e) => {
                setTextContent(e.target.value);
                setAnalysisResult(null);
              }}
              disabled={isAnalyzing}
            />
            <div className="syllabus-char-count">
              {textContent.length.toLocaleString()} characters
            </div>
          </div>
        )}

        {/* Action Trigger */}
        {!analysisResult && (
          <div className="syllabus-analyze-action-row">
            <button
              type="button"
              id="btn-analyze-syllabus"
              className="btn-primary syllabus-analyze-btn"
              onClick={handleAnalyze}
              disabled={isAnalyzing || (activeTab === 'file' && !selectedFile) || (activeTab === 'text' && !textContent.trim())}
            >
              <Sparkles size={14} className={isAnalyzing ? 'animate-spin' : ''} />
              <span>{isAnalyzing ? 'Analyzing Syllabus with AI...' : 'Analyze & Map to MCAT Outline'}</span>
            </button>
          </div>
        )}

        {/* Analysis Results Display */}
        {analysisResult && (
          <div className="syllabus-results-card">
            <div className="syllabus-result-header">
              <div className="syllabus-result-title-group">
                <CheckCircle2 size={16} className="syllabus-success-icon" />
                <span className="syllabus-result-title">AAMC Taxonomy Match Found</span>
              </div>
              <div className="syllabus-result-confidence">
                {Math.round((analysisResult.confidence || 0.9) * 100)}% Confidence
              </div>
            </div>

            <div className="syllabus-result-grid">
              <div className="syllabus-result-item">
                <span className="syllabus-result-label">Detected Section:</span>
                <span className="syllabus-result-value syllabus-highlight">
                  {analysisResult.section_name || analysisResult.section}
                </span>
              </div>

              <div className="syllabus-result-item">
                <span className="syllabus-result-label">Primary Topic:</span>
                <span className="syllabus-result-value">
                  {analysisResult.topic}
                </span>
              </div>

              {analysisResult.subtopic && (
                <div className="syllabus-result-item full-width">
                  <span className="syllabus-result-label">Target Subtopic:</span>
                  <span className="syllabus-result-value syllabus-muted">
                    {analysisResult.subtopic}
                  </span>
                </div>
              )}
            </div>

            {analysisResult.summary && (
              <div className="syllabus-result-summary">
                <BookOpen size={14} />
                <span>{analysisResult.summary}</span>
              </div>
            )}

            {/* Suggested Batch Sets */}
            {analysisResult.suggested_batches && analysisResult.suggested_batches.length > 0 && (
              <div className="syllabus-suggested-batches">
                <div className="syllabus-suggested-label">
                  <Layers size={13} />
                  <span>Proposed Batch Set Scenarios:</span>
                </div>
                <div className="syllabus-batch-list">
                  {analysisResult.suggested_batches.map((b, idx) => (
                    <div key={idx} className="syllabus-batch-item">
                      <span className="syllabus-batch-num">Set #{idx + 1}</span>
                      <span className="syllabus-batch-angle">{b.thematic_angle}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Apply Button */}
            <div className="syllabus-result-actions">
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setAnalysisResult(null)}
              >
                Analyze Another
              </button>
              <button
                type="button"
                id="btn-apply-syllabus-wizard"
                className="btn-primary syllabus-apply-btn"
                onClick={handleApplyToWizard}
              >
                <span>Apply to Generator Wizard</span>
                <ArrowRight size={14} />
              </button>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
}
