import { TRAP_PATTERN_STR } from '../../constants/mcatTraps';

/**
 * Lightweight inline markdown & trap highlighter.
 * Converts bold (**text**) and italic (*text*) tokens to HTML elements,
 * and highlights recognized AAMC cognitive trap names.
 *
 * @param {string} text - Raw input text
 * @param {object} options - Options object
 * @param {boolean} options.highlightTraps - Whether to highlight cognitive traps
 * @returns {Array<React.ReactNode>|null}
 */
function renderFormattedText(text, { highlightTraps = false } = {}) {
  if (!text) return null;

  const pattern = highlightTraps
    ? `(${TRAP_PATTERN_STR}|\\*\\*[^*]+\\*\\*|\\*[^*]+\\*)`
    : '(\\*\\*[^*]+\\*\\*|\\*[^*]+\\*)';

  const tokenRegex = new RegExp(pattern, 'gi');
  const parts = text.split(tokenRegex);

  return parts.map((part, i) => {
    if (!part) return null;
    const itemKey = `fmt-${i}-${part.slice(0, 10)}`;

    if (highlightTraps && new RegExp(`^${TRAP_PATTERN_STR}$`, 'i').test(part)) {
      return (
        <span
          key={itemKey}
          style={{
            background: 'rgba(245, 158, 11, 0.16)',
            color: 'var(--status-warning)',
            border: '1px solid var(--status-warning-border, rgba(245, 158, 11, 0.3))',
            borderRadius: '3px',
            padding: '1px 6px',
            fontWeight: 700,
            fontSize: '0.74rem',
            margin: '0 2px',
            display: 'inline-block',
            lineHeight: 1.35,
            verticalAlign: 'baseline'
          }}
        >
          {part}
        </span>
      );
    }

    if (part.startsWith('**') && part.endsWith('**') && part.length >= 4) {
      return (
        <strong key={itemKey} style={{ color: 'var(--text-primary)', fontWeight: 700 }}>
          {part.slice(2, -2)}
        </strong>
      );
    }

    if (part.startsWith('*') && part.endsWith('*') && part.length >= 2) {
      return <em key={itemKey}>{part.slice(1, -1)}</em>;
    }

    return part;
  });
}

/**
 * FormattedText declarative React component.
 * Renders bold (**text**), italic (*text*), and highlighted AAMC cognitive traps.
 */
export default function FormattedText({ text, highlightTraps = false, className, style }) {
  const content = renderFormattedText(text, { highlightTraps });
  if (!content) return null;
  return (
    <span className={className} style={style}>
      {content}
    </span>
  );
}
