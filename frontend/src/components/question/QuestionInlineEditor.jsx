import React from 'react';
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
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '10px 14px',
        background: 'var(--status-warning-bg)',
        border: '1px solid var(--status-warning-border)',
        borderRadius: 'var(--radius-md)',
        color: 'var(--status-warning)',
        fontSize: '0.8rem'
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 600 }}>
        <Edit3 size={14} />
        <span>Editing Question. Make your changes below and click Save.</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
        <button
          type="button"
          onClick={onSave}
          className="btn-success"
          style={{ padding: '5px 10px', fontSize: '0.75rem' }}
        >
          <Save size={12} /> Save
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="btn-secondary"
          style={{ padding: '5px 10px', fontSize: '0.75rem' }}
        >
          <X size={12} /> Cancel
        </button>
      </div>
    </div>
  );
}
