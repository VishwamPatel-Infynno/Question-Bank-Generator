
/**
 * Infynno Solutions LLP Official Vector Logo
 * Features the signature gradient #4F30B9 -> #335ACF -> #1E7ADF
 */
const EMPTY_OBJECT = Object.freeze({});

export default function InfynnoLogo({
  width = 34,
  height = 22,
  className = '',
  style = EMPTY_OBJECT,
  showText = false,
  textColor = 'var(--text-primary)'
}) {
  const gradientId = 'infynno-brand-gradient';

  return (
    <div
      className={className}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '8px',
        lineHeight: 1,
        ...style
      }}
      title="Infynno Solutions LLP - Infinite Innovations"
    >
      <svg
        width={width}
        height={height}
        viewBox="90 20 1130 695"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        preserveAspectRatio="xMidYMid meet"
        style={{ flexShrink: 0, display: 'block' }}
        aria-label="Infynno Solutions Logo"
      >
        <defs>
          <linearGradient id={gradientId} x1="98" y1="368" x2="1210" y2="368" gradientUnits="userSpaceOnUse">
            <stop stopColor="#4F30B9" />
            <stop offset="0.5" stopColor="#335ACF" />
            <stop offset="1" stopColor="#1E7ADF" />
          </linearGradient>
        </defs>
        <path
          d="M1171.37 210.163C1150.33 210.163 1133.31 227.18 1133.31 248.222V549.875C1133.31 578.975 1117.64 603.832 1091.44 616.37C1065.25 628.908 1035.92 625.776 1013.31 607.411L714.65 368.535L1000.33 130.316C1010.41 123.377 1017.12 111.96 1017.12 98.7479C1017.12 77.7057 1000.1 60.6881 979.056 60.6881C971.217 60.6881 963.832 63.1467 957.787 67.1802C956.894 67.6264 956.22 68.3001 955.319 68.9738L653.754 319.722L341.664 70.3212C296.219 33.8275 235.542 26.8892 183.16 52.1837C130.55 77.2594 98.0808 129.196 98.0808 187.405V549.866C98.0808 608.076 130.541 659.793 183.16 685.088C235.551 710.164 296.438 703.225 341.664 666.95L653.754 417.322L965.617 666.95C992.933 688.894 1025.84 700.084 1059.2 700.084C1081.14 700.084 1103.53 695.158 1124.36 685.088C1176.97 659.793 1209.43 608.076 1209.43 549.866V248.222C1209.43 227.18 1192.41 210.163 1171.37 210.163ZM294.198 607.411C271.362 625.767 242.253 628.908 216.066 616.37C189.871 603.832 174.2 578.984 174.2 549.875V187.414C174.2 158.314 189.871 133.238 216.066 120.7C226.592 115.774 237.555 113.316 248.308 113.316C264.652 113.316 280.549 118.688 294.207 129.659L592.859 368.535L294.198 607.411ZM1209.44 75.1946C1209.44 96.2106 1192.39 113.254 1171.38 113.254C1150.36 113.254 1133.32 96.2106 1133.32 75.1946C1133.32 54.1786 1150.36 37.1348 1171.38 37.1348C1192.4 37.1348 1209.44 54.1698 1209.44 75.1946Z"
          fill={`url(#${gradientId})`}
        />
      </svg>
      {showText && (
        <span
          style={{
            fontWeight: 800,
            fontSize: '0.85rem',
            letterSpacing: '0.04em',
            color: textColor
          }}
        >
          INFYNNO
        </span>
      )}
    </div>
  );
}
