import { useState, memo } from 'react';
import {
  Sparkles,
  Loader2,
  ChevronDown,
  ChevronUp,
  Check,
  X,
  CornerDownLeft
} from 'lucide-react';

function QuestionCopilotStrip({
  isCopilotWorking = false,
  copilotStatusText = '',
  handleCopilotAction,
  previewQuestion = null,
  onApplyPreview,
  onDiscardPreview
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [customPrompt, setCustomPrompt] = useState('');

  const handleCustomSubmit = (e) => {
    if (e) e.preventDefault();
    const prompt = customPrompt.trim();
    if (!prompt || isCopilotWorking) return;
    handleCopilotAction('custom', prompt, 'Applying Custom AI Instruction');
  };

  const handleQuickAction = (action, instruction, label) => {
    setIsOpen(true);
    handleCopilotAction(action, instruction, label);
  };

  return (
    <div className={`qcard-ai-copilot-drawer ${isOpen || previewQuestion ? 'open' : ''}`}>
      {/* Header Bar */}
      <div className="qcard-ai-copilot-header">
        <button
          type="button"
          className="qcard-ai-copilot-toggle-btn"
          onClick={() => setIsOpen((prev) => !prev)}
          aria-expanded={isOpen || Boolean(previewQuestion)}
        >
          <Sparkles size={13} color="var(--brand-primary)" />
          <span className="qcard-ai-copilot-title">AI Editorial Copilot</span>
          {isOpen || previewQuestion ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
        </button>

        {isCopilotWorking && (
          <span className="qcard-ai-copilot-status">
            <Loader2 size={12} className="animate-spin" />
            <span>{copilotStatusText}...</span>
          </span>
        )}

        {!isOpen && !previewQuestion && !isCopilotWorking && (
          <div className="qcard-ai-copilot-quick-pills">
            <button
              type="button"
              className="qcard-ai-copilot-btn"
              disabled={isCopilotWorking}
              onClick={() =>
                handleQuickAction(
                  'polish_distractor',
                  'Polish distractors for strict length symmetry and authentic AAMC traps',
                  'Polishing Distractors'
                )
              }
            >
              <span>Polish Distractors</span>
            </button>
            <button
              type="button"
              className="qcard-ai-copilot-btn"
              disabled={isCopilotWorking}
              onClick={() =>
                handleQuickAction(
                  'simplify_explanation',
                  'Simplify explanation into clear, step-by-step mentor reasoning',
                  'Simplifying Explanation'
                )
              }
            >
              <span>Simplify Explanation</span>
            </button>
            <button
              type="button"
              className="qcard-ai-copilot-btn"
              disabled={isCopilotWorking}
              onClick={() =>
                handleQuickAction(
                  'invert_sibling',
                  'Invert perspective to test the reciprocal relationship',
                  'Inverting Sibling'
                )
              }
            >
              <span>Invert Sibling</span>
            </button>
          </div>
        )}
      </div>

      {/* Expanded Drawer Content */}
      {(isOpen || previewQuestion) && (
        <div className="qcard-ai-copilot-body">
          {/* Conversational Custom Prompt Form */}
          <form onSubmit={handleCustomSubmit} className="qcard-ai-copilot-form">
            <input
              type="text"
              value={customPrompt}
              onChange={(e) => setCustomPrompt(e.target.value)}
              placeholder="Tell AI how to refine... e.g. Make Option C trickier on competitive vs non-competitive inhibition"
              className="qcard-ai-copilot-input"
              disabled={isCopilotWorking}
            />
            <button
              type="submit"
              disabled={isCopilotWorking || !customPrompt.trim()}
              className="qcard-ai-copilot-submit-btn"
            >
              {isCopilotWorking ? (
                <Loader2 size={12} className="animate-spin" />
              ) : (
                <CornerDownLeft size={12} />
              )}
              <span>Refine</span>
            </button>
          </form>

          {/* Quick Action Chips Strip */}
          <div className="qcard-ai-copilot-chips-wrap">
            <span className="qcard-ai-copilot-chips-label">Quick Prompts:</span>
            <button
              type="button"
              className="qcard-ai-copilot-btn"
              disabled={isCopilotWorking}
              onClick={() =>
                handleCopilotAction(
                  'polish_distractor',
                  'Polish distractors for strict length symmetry and authentic AAMC traps',
                  'Polishing Distractors'
                )
              }
            >
              <span>✨ Polish Distractors</span>
            </button>
            <button
              type="button"
              className="qcard-ai-copilot-btn"
              disabled={isCopilotWorking}
              onClick={() =>
                handleCopilotAction(
                  'simplify_explanation',
                  'Simplify explanation into clear, step-by-step mentor reasoning',
                  'Simplifying Explanation'
                )
              }
            >
              <span>💡 Simplify Explanation</span>
            </button>
            <button
              type="button"
              className="qcard-ai-copilot-btn"
              disabled={isCopilotWorking}
              onClick={() =>
                handleCopilotAction(
                  'invert_sibling',
                  'Invert perspective to test the reciprocal relationship',
                  'Inverting Sibling'
                )
              }
            >
              <span>🔄 Invert Sibling</span>
            </button>
          </div>

          {/* Staged Diff Preview Card */}
          {previewQuestion && (
            <div className="qcard-ai-copilot-preview-card">
              <div className="qcard-ai-copilot-preview-header">
                <span className="qcard-ai-copilot-preview-badge">
                  <Sparkles size={11} />
                  <span>Staged AI Refinement Proposal</span>
                </span>
                <div className="qcard-ai-copilot-preview-actions">
                  <button
                    type="button"
                    onClick={onApplyPreview}
                    className="qcard-ai-copilot-apply-btn"
                  >
                    <Check size={12} />
                    <span>Apply Changes</span>
                  </button>
                  <button
                    type="button"
                    onClick={onDiscardPreview}
                    className="qcard-ai-copilot-discard-btn"
                  >
                    <X size={12} />
                    <span>Discard</span>
                  </button>
                </div>
              </div>

              <div className="qcard-ai-copilot-preview-content">
                {previewQuestion.question_stem && (
                  <div className="qcard-ai-copilot-preview-section">
                    <strong>Revised Stem:</strong>
                    <p>{previewQuestion.question_stem}</p>
                  </div>
                )}

                {previewQuestion.options && (
                  <div className="qcard-ai-copilot-preview-section">
                    <strong>Revised Options:</strong>
                    <div className="qcard-ai-copilot-preview-options">
                      {previewQuestion.options.map((opt) => {
                        const isKey = opt.id === previewQuestion.correct_answer_id;
                        return (
                          <div
                            key={opt.id}
                            className={`qcard-ai-copilot-preview-opt ${isKey ? 'correct' : ''}`}
                          >
                            <span className="qcard-ai-copilot-opt-id">{opt.id}.</span>
                            <span>{opt.text}</span>
                            {isKey && <span className="badge-key">Correct Key</span>}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {previewQuestion.explanation && (
                  <div className="qcard-ai-copilot-preview-section">
                    <strong>Revised Explanation:</strong>
                    <p className="qcard-ai-copilot-preview-explanation">
                      {previewQuestion.explanation}
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default memo(QuestionCopilotStrip);
