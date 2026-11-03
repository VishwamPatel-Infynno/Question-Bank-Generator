import React from 'react';
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
    <header
      style={{
        display: 'grid',
        gridTemplateColumns: '1fr auto 1fr',
        alignItems: 'center',
        padding: '10px 24px',
        borderBottom: '1px solid var(--border-light)',
        background: 'var(--bg-surface)',
        position: 'sticky',
        top: 0,
        zIndex: 50,
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)'
      }}
    >
      {/* Brand & Subtitle */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px', justifySelf: 'start', minWidth: 0 }}>
        {/* Infynno Solutions Logo & Corporate Anchor */}
        <a
          href="https://infynno.com/"
          target="_blank"
          rel="noopener noreferrer"
          title="Visit Infynno Solutions LLP (https://infynno.com)"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            textDecoration: 'none',
            padding: '4px 8px',
            borderRadius: 'var(--radius-sm)',
            background: 'var(--bg-surface-subtle)',
            border: '1px solid var(--border-light)',
            transition: 'all var(--transition-fast)'
          }}
        >
          <InfynnoLogo width={26} height={17} />
          <span
            style={{
              fontWeight: 800,
              fontSize: '0.725rem',
              letterSpacing: '0.05em',
              color: 'var(--text-primary)'
            }}
          >
            INFYNNO
          </span>
        </a>

        {/* Hairline Divider */}
        <div
          style={{
            width: '1px',
            height: '18px',
            background: 'var(--border-light)'
          }}
          aria-hidden="true"
        />

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
          className="brand-refresh-link"
          title="Return to home"
          aria-label="Infynno MCAT Question Studio home - click to return to home"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            textDecoration: 'none',
            cursor: 'pointer'
          }}
        >
          <h1
            style={{
              fontSize: '0.875rem',
              fontWeight: 600,
              letterSpacing: '-0.01em',
              color: 'var(--text-primary)',
              margin: 0,
              transition: 'color var(--transition-fast)'
            }}
          >
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
            <span
              style={{
                background: 'var(--border-medium)',
                color: 'var(--text-secondary)',
                borderRadius: 'var(--radius-full)',
                fontSize: '0.625rem',
                fontWeight: 600,
                padding: '1px 5px',
                lineHeight: 1
              }}
            >
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
            <span
              style={{
                background: 'var(--border-medium)',
                color: 'var(--text-secondary)',
                borderRadius: 'var(--radius-full)',
                fontSize: '0.625rem',
                fontWeight: 600,
                padding: '1px 5px',
                lineHeight: 1
              }}
            >
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
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', justifySelf: 'end', minWidth: 0 }}>

        {/* Backend Status Indicator */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '4px 8px',
            background: 'var(--bg-surface-subtle)',
            borderRadius: 'var(--radius-xs)',
            fontSize: '0.7rem',
            fontWeight: 500,
            border: '1px solid var(--border-light)'
          }}
        >
          <span
            style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              background: backendStatus ? 'var(--status-success)' : 'var(--status-warning)'
            }}
          />
          <span style={{ color: 'var(--text-secondary)' }}>
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
