import { useState } from 'react';
import {
  ArrowRight,
  BookOpen,
  Database,
  FlaskConical,
  Dna,
  Brain,
  Sparkles,
  Loader2,
  FileText
} from 'lucide-react';
import InfynnoLogo from '../common/InfynnoLogo';
import { HERO_PRESETS } from './wizardConstants';
import { fetchMagicSetup } from '../../services/api';
import { SyllabusIngestionModal } from '../modals';

const HERO_PRESET_ICONS = Object.freeze({
  chem_phys: FlaskConical,
  cars: BookOpen,
  bio_biochem: Dna,
  psych_soc: Brain
});

const MAGIC_SUGGESTIONS = Object.freeze([
  'Renal clearance & acid-base regulation (10 questions, physiology trace, hard)',
  'Enzyme kinetics & competitive vs allosteric inhibition (5 questions, high)',
  'CARS epistemology & historical revisionism passage set (5 questions)',
  'Fluid hemodynamics & Bernoulli pressure-volume loops (10 questions)'
]);

export default function HeroLanding({
  onGetStarted,
  onOpenBank,
  onApplyPreset
}) {
  const [magicPrompt, setMagicPrompt] = useState('');
  const [isParsing, setIsParsing] = useState(false);
  const [magicError, setMagicError] = useState('');
  const [isSyllabusModalOpen, setIsSyllabusModalOpen] = useState(false);

  const handleApplySyllabus = (result) => {
    if (onApplyPreset) {
      onApplyPreset({
        section: result.section,
        topic: result.topic,
        subtopic: result.subtopic,
        difficulty: result.difficulty || 'medium',
        additional_instructions: result.suggested_instructions || '',
        thematic_angle: result.suggested_batches?.[0]?.thematic_angle || ''
      });
    }
  };

  const handleMagicSubmit = async (e) => {
    if (e) e.preventDefault();
    const query = magicPrompt.trim();
    if (!query || isParsing) return;
    setIsParsing(true);
    setMagicError('');
    try {
      const cfg = await fetchMagicSetup(query);
      if (onApplyPreset) {
        onApplyPreset({
          section: cfg.section,
          difficulty: cfg.difficulty,
          totalQuestions: cfg.questions_to_generate,
          topic: cfg.topic,
          subtopic: cfg.subtopic,
          visualType: cfg.visual_type,
          primaryTrap: cfg.primary_trap,
          passageMode: cfg.passage_mode,
          additionalInstructions: cfg.additional_instructions
        });
      }
    } catch (err) {
      setMagicError(err.message || 'Failed to configure with AI. Please try again.');
    } finally {
      setIsParsing(false);
    }
  };

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

        {/* Natural Language AI Magic Setup */}
        <form onSubmit={handleMagicSubmit} className="hero-magic-container">
          <div className="hero-magic-bar">
            <div className="hero-magic-icon-wrap">
              <Sparkles size={16} className="hero-magic-sparkle-icon" />
            </div>
            <input
              type="text"
              value={magicPrompt}
              onChange={(e) => setMagicPrompt(e.target.value)}
              placeholder="Describe what you want to create... e.g. 10 hard questions on renal clearance with an ECG trace"
              className="hero-magic-input"
              disabled={isParsing}
            />
            <button
              type="submit"
              disabled={isParsing || !magicPrompt.trim()}
              className="hero-magic-btn"
              title="Configure with AI"
            >
              {isParsing ? (
                <>
                  <Loader2 size={13} className="animate-spin" />
                  <span>Configuring...</span>
                </>
              ) : (
                <>
                  <Sparkles size={13} />
                  <span>Configure with AI</span>
                </>
              )}
            </button>
          </div>

          <div className="hero-magic-suggestions">
            <span className="hero-magic-label">Try prompt:</span>
            {MAGIC_SUGGESTIONS.map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                className="hero-magic-chip"
                onClick={() => setMagicPrompt(suggestion)}
              >
                <span>{suggestion.split('(')[0].trim()}</span>
              </button>
            ))}
          </div>

          {magicError && (
            <div className="hero-magic-error">{magicError}</div>
          )}
        </form>

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

          <button
            type="button"
            className="hero-secondary-cta"
            id="btn-hero-ingest-syllabus"
            onClick={() => setIsSyllabusModalOpen(true)}
            title="Upload a course syllabus or outline to configure the wizard automatically"
          >
            <FileText size={15} />
            <span>Ingest Syllabus / PDF</span>
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
                >
                  <Icon size={13} className="hero-landing-preset-icon" />
                  <span>{preset.label}</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      <SyllabusIngestionModal
        isOpen={isSyllabusModalOpen}
        onClose={() => setIsSyllabusModalOpen(false)}
        onApply={handleApplySyllabus}
      />
    </div>
  );
}
