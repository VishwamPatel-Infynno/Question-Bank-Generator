import { Edit3, Save, X } from 'lucide-react';

/**
 * QuestionInlineEditor:
 * Renders the top notification banner and action controls when a question is in Quick Edit Mode.
 *
 * Props:
 * - onSave: () => void - Callback triggered when educator confirms edits
 * - onCancel: () => void - Callback triggered when educator cancels edits
 */
export default function QuestionInlineEditor({ onSave, onCancel }) {
  return (
    <div className="qcard-edit-banner">
      <div className="qcard-edit-title">
        <Edit3 size={14} />
        <span>Editing Question</span>
      </div>
      <div className="qcard-edit-actions">
        <button
          type="button"
          onClick={onSave}
          className="btn-success qcard-edit-btn"
        >
          <Save size={12} /> Save
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="btn-secondary qcard-edit-btn"
        >
          <X size={12} /> Cancel
        </button>
      </div>
    </div>
  );
}
