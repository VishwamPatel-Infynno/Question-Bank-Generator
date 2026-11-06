import { CheckCircle2 } from 'lucide-react';

/**
 * One selectable card in a wizard decision grid: a native button (keyboard and screen-reader
 * behaviour for free) that shows a check mark while selected.
 */
export default function WizardChoiceCard({ selected = false, onSelect, className = '', id, children }) {
  return (
    <button
      type="button"
      id={id}
      className={`wizard-tier-card ${className} ${selected ? 'selected' : ''}`.replace(/\s+/g, ' ').trim()}
      onClick={onSelect}
      aria-pressed={selected}
    >
      <div className="wizard-tier-card-content">
        {children}
        {selected && <CheckCircle2 size={14} color="var(--brand-primary)" />}
      </div>
    </button>
  );
}
