import { ExternalLink } from 'lucide-react';

const CURRENT_YEAR = new Date().getFullYear();

export default function Footer() {
  return (
    <footer className="footer-container">
      <div className="footer-inner">
        {/* Left: Product & Platform Identity */}
        <div className="footer-brand">
          <span className="footer-product-name">MCAT Question Studio</span>
          <span className="footer-separator" aria-hidden="true">•</span>
          <span className="footer-tagline">AI-Powered Exam Authoring & Psychometric Verification</span>
        </div>

        {/* Right: Copyright & Corporate Link */}
        <div className="footer-links">
          <span className="footer-copyright">
            © {CURRENT_YEAR} Infynno Solutions LLP
          </span>
          <a
            href="https://infynno.com/"
            target="_blank"
            rel="noopener noreferrer"
            className="infynno-pill-link"
            title="Visit Infynno Solutions LLP (https://infynno.com)"
          >
            <span>infynno.com</span>
            <ExternalLink size={10} />
          </a>
        </div>
      </div>
    </footer>
  );
}
