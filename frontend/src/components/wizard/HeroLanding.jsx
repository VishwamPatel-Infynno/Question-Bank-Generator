import {
  ArrowRight,
  BookOpen,
  Database,
  FlaskConical,
  Dna,
  Brain
} from 'lucide-react';
import InfynnoLogo from '../common/InfynnoLogo';
import { HERO_PRESETS } from './wizardConstants';

const HERO_PRESET_ICONS = Object.freeze({
  chem_phys: FlaskConical,
  cars: BookOpen,
  bio_biochem: Dna,
  psych_soc: Brain
});

export default function HeroLanding({
  onGetStarted,
  onOpenBank,
  onApplyPreset
}) {
  return (
    <div className="hero-wrapper" id="hero-landing-view">
      <div className="hero-content">
        {/* Infynno Logo Anchor */}
        <div className="hero-landing-badge-wrap">
          <a
            href="https://infynno.com/"
            target="_blank"
            rel="noopener noreferrer"
            title="Infynno Solutions"
            aria-label="Infynno Solutions (opens in a new tab)"
            className="hero-landing-badge-inline"
          >
            <InfynnoLogo width={44} height={28} />
          </a>
        </div>

        {/* Hero Title */}
        <h1 className="hero-title">
          MCAT Question Studio
        </h1>

        {/* Tagline */}
        <p className="hero-tagline">
          Create MCAT questions with passages, diagrams, and explanations.
        </p>

        {/* Centered CTA Buttons */}
        <div className="hero-cta-group">
          <button
            type="button"
            className="hero-primary-cta"
            id="btn-hero-get-started"
            onClick={onGetStarted}
          >
            <span>Create Questions</span>
            <ArrowRight size={16} aria-hidden="true" />
          </button>

          <button
            type="button"
            className="hero-secondary-cta"
            id="btn-hero-open-bank"
            onClick={onOpenBank}
          >
            <Database size={15} aria-hidden="true" />
            <span>Question Bank</span>
          </button>
        </div>

        {/* Quiet Preset Quick-Starts */}
        <div className="hero-presets-container">
          <div className="hero-presets-label">Presets:</div>
          <div className="hero-presets-chips">
            {HERO_PRESETS.map((preset) => {
              const Icon = HERO_PRESET_ICONS[preset.sectionId] || FlaskConical;
              return (
                <button
                  key={preset.label}
                  type="button"
                  className="hero-preset-chip"
                  onClick={() => onApplyPreset(preset.config)}
                  title={`Start with ${preset.label}`}
                  aria-label={`Start with ${preset.label} preset`}
                >
                  <Icon size={13} className="hero-landing-preset-icon" aria-hidden="true" />
                  <span>{preset.label}</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
