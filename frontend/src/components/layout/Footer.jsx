import { ExternalLink } from 'lucide-react';
import InfynnoLogo from '../common/InfynnoLogo';

const CURRENT_YEAR = new Date().getFullYear();

export default function Footer() {
  return (
    <footer
      style={{
        marginTop: 'auto',
        borderTop: '1px solid var(--border-light)',
        background: 'var(--bg-surface)',
        padding: '14px 24px',
        color: 'var(--text-secondary)',
        fontSize: '0.75rem'
      }}
    >
      <div
        style={{
          maxWidth: '1440px',
          margin: '0 auto',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px'
        }}
      >
        {/* Left: Brand Identity */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <a
            href="https://infynno.com/"
            target="_blank"
            rel="noopener noreferrer"
            style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', textDecoration: 'none' }}
            title="Infynno Solutions LLP"
          >
            <InfynnoLogo width={24} height={15} showText={true} />
          </a>
        </div>

        {/* Right: Link & Copyright */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          <a
            href="https://infynno.com/"
            target="_blank"
            rel="noopener noreferrer"
            className="infynno-pill-link"
            style={{ padding: '3px 8px', fontSize: '0.7rem' }}
          >
            <span>infynno.com</span>
            <ExternalLink size={10} />
          </a>
          <span style={{ color: 'var(--text-muted)' }}>
            © {CURRENT_YEAR} Infynno Solutions LLP
          </span>
        </div>
      </div>
    </footer>
  );
}

