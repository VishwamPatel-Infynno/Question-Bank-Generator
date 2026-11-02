import React from 'react';
import {
  ArrowRight,
  BookOpen,
  Database,
  FlaskConical,
  Dna,
  Brain
} from 'lucide-react';
import InfynnoLogo from '../common/InfynnoLogo';

export default function HeroLanding({
  onGetStarted,
  onOpenBank,
  onApplyPreset
}) {
  const PRESETS = [
    {
      label: 'Chem / Phys',
      tag: '50 Questions',
      icon: FlaskConical,
      config: {
        section: 'chem_phys',
        difficulty: 'medium',
        totalQuestions: 50,
        singleChoiceCount: 50,
        passageMode: 'single_passage',
        passageQuestionCount: 50,
        passageCount: 10,
        passageRequired: 'Yes'
      }
    },
    {
      label: 'CARS',
      tag: '50 Questions',
      icon: BookOpen,
      config: {
        section: 'cars',
        difficulty: 'medium',
        totalQuestions: 50,
        singleChoiceCount: 50,
        passageCount: 10,
        passageMode: 'single_passage',
        passageQuestionCount: 50,
        passageRequired: 'Yes'
      }
    },
    {
      label: 'Bio / Biochem',
      tag: '50 Questions',
      icon: Dna,
      config: {
        section: 'bio_biochem',
        difficulty: 'hard',
        totalQuestions: 50,
        singleChoiceCount: 50,
        passageMode: 'single_passage',
        passageQuestionCount: 50,
        passageCount: 10,
        passageRequired: 'Yes'
      }
    },
    {
      label: 'Psych / Soc',
      tag: '50 Questions',
      icon: Brain,
      config: {
        section: 'psych_soc',
        difficulty: 'medium',
        totalQuestions: 50,
        singleChoiceCount: 50,
        passageMode: 'independent',
        passageQuestionCount: 0,
        passageCount: 0,
        passageRequired: 'No'
      }
    }
  ];

  return (
    <div className="hero-wrapper" id="hero-landing-view">
      <div className="hero-content">
        {/* Infynno Logo Anchor */}
        <div style={{ marginBottom: '14px' }}>
          <a
            href="https://infynno.com/"
            target="_blank"
            rel="noopener noreferrer"
            title="Infynno Solutions"
            style={{ display: 'inline-block' }}
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
          Generate MCAT questions with passages, diagrams, and explanations.
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
            <ArrowRight size={16} />
          </button>

          <button
            type="button"
            className="hero-secondary-cta"
            id="btn-hero-open-bank"
            onClick={onOpenBank}
          >
            <Database size={15} />
            <span>Question Bank</span>
          </button>
        </div>

        {/* Quiet Preset Quick-Starts */}
        <div className="hero-presets-container">
          <div className="hero-presets-label">Presets:</div>
          <div className="hero-presets-chips">
            {PRESETS.map((preset) => {
              const Icon = preset.icon;
              return (
                <button
                  key={preset.label}
                  type="button"
                  className="hero-preset-chip"
                  onClick={() => onApplyPreset(preset.config)}
                  title={`Start with ${preset.label} (${preset.tag})`}
                >
                  <Icon size={13} style={{ color: 'var(--brand-primary)' }} />
                  <span>{preset.label}</span>
                  <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{preset.tag}</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
