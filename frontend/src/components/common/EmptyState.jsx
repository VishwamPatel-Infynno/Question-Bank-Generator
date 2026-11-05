/**
 * EmptyState - the shared "nothing to show here" panel: icon, title, description and optional
 * action buttons. `LoadError` builds on it, so every empty or failed list looks alike.
 * @param {Object} props
 * @param {React.ReactNode} props.icon - Icon element shown in the round badge.
 * @param {string} [props.iconTone] - Extra class on the badge ('success', 'load-error-icon', ...).
 * @param {string} props.title
 * @param {React.ReactNode} [props.description]
 * @param {React.ReactNode} [props.children] - Action buttons.
 * @param {string} [props.role] - e.g. 'alert' for error states.
 */
export default function EmptyState({ icon, iconTone = '', title, description, children, role }) {
  return (
    <div className="view-empty-state" role={role}>
      <div className={`view-empty-icon-box ${iconTone}`.trim()}>{icon}</div>
      <div>
        <h3 className="view-empty-title">{title}</h3>
        {description && <p className="view-empty-desc">{description}</p>}
      </div>
      {children && <div className="view-empty-actions">{children}</div>}
    </div>
  );
}
