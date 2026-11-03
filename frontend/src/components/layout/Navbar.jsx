import { Sparkles, Database, BookOpen, Layers, CheckCircle2, Sun, Moon } from 'lucide-react';
import InfynnoLogo from '../common/InfynnoLogo';

export default function Navbar({
  activeTab,
  setActiveTab,
  onNavigateToGenerator,
  onNavigateToPassages,
  backendStatus,
  theme,
  onToggleTheme,
  onGoHome,
  activeBatchCount = 0,
  validatedCount = 0
}) {
  return (
    <header className="navbar-header">
      {/* Brand & Subtitle */}
      <div className="navbar-brand-section">
        {/* Infynno Solutions Logo & Corporate Anchor */}
        <a
          href="https://infynno.com/"
          target="_blank"
          rel="noopener noreferrer"
          title="Visit Infynno Solutions LLP (https://infynno.com)"
          className="navbar-brand-anchor"
        >
          <InfynnoLogo width={26} height={17} />
          <span className="navbar-brand-text">
            INFYNNO
          </span>
        </a>

        {/* Hairline Divider */}
        <div className="navbar-divider" aria-hidden="true" />

        {/* Product Identity */}
        <a
          href="/"
          onClick={(e) => {
            e.preventDefault();
            if (onGoHome) {
              onGoHome();
            } else {
              window.location.href = '/';
            }
          }}
          className="brand-refresh-link navbar-brand-title-link"
          title="Return to home"
          aria-label="Infynno MCAT Question Studio home - click to return to home"
        >
          <h1 className="navbar-product-title">
            MCAT Question Studio
          </h1>
        </a>
      </div>

      {/* Center Nav Tabs (Quiet Minimalist Pill Track) */}
      <nav className="pill-track" style={{ justifySelf: 'center' }}>
        <button
          id="nav-tab-generator"
          type="button"
          onClick={() => {
            if (onNavigateToGenerator) {
              onNavigateToGenerator();
            } else {
              setActiveTab('generator');
            }
          }}
          className={`pill-track-btn ${activeTab === 'generator' ? 'active' : ''}`}
          title="Create Questions"
        >
          <Sparkles size={12} color={activeTab === 'generator' ? 'var(--brand-primary)' : 'currentColor'} />
          <span>Create</span>
        </button>

        <button
          id="nav-tab-batches"
          type="button"
          onClick={() => setActiveTab('batches')}
          className={`pill-track-btn ${activeTab === 'batches' ? 'active' : ''}`}
          style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
          title="Batch Progress"
        >
          <Layers size={12} color={activeTab === 'batches' ? 'var(--brand-primary)' : 'currentColor'} />
          <span>Batches</span>
          {activeBatchCount > 0 && (
            <span className="navbar-pill-count">
              {activeBatchCount}
            </span>
          )}
        </button>

        <button
          id="nav-tab-validated"
          type="button"
          onClick={() => setActiveTab('validated')}
          className={`pill-track-btn ${activeTab === 'validated' ? 'active' : ''}`}
          style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
          title="Review Queue"
        >
          <CheckCircle2 size={12} color={activeTab === 'validated' ? 'var(--brand-primary)' : 'currentColor'} />
          <span>Review</span>
          {validatedCount > 0 && (
            <span className="navbar-pill-count">
              {validatedCount}
            </span>
          )}
        </button>

        <button
          id="nav-tab-bank"
          type="button"
          onClick={() => setActiveTab('bank')}
          className={`pill-track-btn ${activeTab === 'bank' ? 'active' : ''}`}
          title="Question Bank"
        >
          <Database size={12} color={activeTab === 'bank' ? 'var(--brand-primary)' : 'currentColor'} />
          <span>Question Bank</span>
        </button>

        <button
          id="nav-tab-passages"
          type="button"
          onClick={() => {
            if (onNavigateToPassages) {
              onNavigateToPassages();
            } else {
              setActiveTab('passages');
            }
          }}
          className={`pill-track-btn ${activeTab === 'passages' ? 'active' : ''}`}
          title="Passage Bank"
        >
          <BookOpen size={12} color={activeTab === 'passages' ? 'var(--brand-primary)' : 'currentColor'} />
          <span>Passage Bank</span>
        </button>
      </nav>

      {/* Right Tools */}
      <div className="navbar-tools">
        {/* Backend Status Indicator */}
        <div className="navbar-status-indicator">
          <span
            className={`navbar-status-dot ${backendStatus ? 'online' : 'offline'}`}
          />
          <span className="navbar-status-text">
            {backendStatus ? 'Online' : 'Connecting...'}
          </span>
        </div>

        {/* Theme Switcher Button */}
        <button
          id="btn-toggle-theme"
          onClick={onToggleTheme}
          className="btn-secondary"
          style={{ padding: '5px 8px', fontSize: '0.75rem', borderRadius: 'var(--radius-xs)' }}
          title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode (Press T)`}
        >
          {theme === 'dark' ? <Sun size={13} color="var(--status-warning)" /> : <Moon size={13} color="var(--infynno-blue)" />}
          <span className="kbd-hint" style={{ fontSize: '0.575rem', padding: '1px 3px', marginLeft: '3px' }}>T</span>
        </button>
      </div>
    </header>
  );
}
