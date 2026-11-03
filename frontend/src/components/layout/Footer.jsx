import { ExternalLink } from 'lucide-react';
import InfynnoLogo from '../common/InfynnoLogo';

const CURRENT_YEAR = new Date().getFullYear();

export default function Footer() {
  return (
    <footer className="footer-container">
      <div className="footer-inner">
        {/* Left: Brand Identity */}
        <div className="footer-brand">
          <a
            href="https://infynno.com/"
            target="_blank"
            rel="noopener noreferrer"
            title="Infynno Solutions LLP"
          >
            <InfynnoLogo width={24} height={15} showText={true} />
          </a>
        </div>

        {/* Right: Link & Copyright */}
        <div className="footer-links">
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
          <span className="footer-copyright">
            © {CURRENT_YEAR} Infynno Solutions LLP
          </span>
        </div>
      </div>
    </footer>
  );
}

