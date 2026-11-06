import { useMemo } from 'react';
import {
  Sparkles,
  CheckCircle2,
  Atom,
  Layers,
  BookOpen,
  Check,
  Compass
} from 'lucide-react';
import { EMPTY_ARRAY, EMPTY_OBJECT, getSubjectsForSection, SECTION_IDS } from '../../../constants';
import { flattenTopics } from '../../../utils/taxonomyHelpers';

export default function WizardStep1SectionFocus({
  selectedSection = SECTION_IDS.CHEM_PHYS,
  onSelectSection,
  SECTION_METADATA = EMPTY_OBJECT,
  selectedSubject = '',
  onSelectSubject,
  onSelectUnit,
  selectedTopic = '',
  onSelectTopic,
  onSelectSubtopic,
  selectedSubtopics = EMPTY_ARRAY,
  onToggleSubtopic,
  presets = EMPTY_ARRAY,
  onApplyPreset,
  totalQuestions = 50
}) {

  // Available subjects for the section
  const subjects = useMemo(() => {
    return getSubjectsForSection(selectedSection);
  }, [selectedSection]);

  const isAllDisciplines = !selectedSubject || selectedSubject === 'all';

  const activeSubject = useMemo(() => {
    if (isAllDisciplines) return null;
    return subjects.find((s) => s.id === selectedSubject) || null;
  }, [subjects, selectedSubject, isAllDisciplines]);

  // Gather available topics (all of the subject's, or the overview selection)
  const availableTopics = useMemo(
    () => flattenTopics(subjects, activeSubject),
    [subjects, activeSubject]
  );

  const isAllTopics = !selectedTopic || selectedTopic === 'all';

  const activeTopic = useMemo(() => {
    if (isAllTopics) return null;
    return availableTopics.find((t) => t.id === selectedTopic) || null;
  }, [availableTopics, selectedTopic, isAllTopics]);

  // Handlers
  const handleSelectAllDisciplines = () => {
    onSelectSubject?.('');
    onSelectUnit?.('');
    onSelectTopic?.('');
    onSelectSubtopic?.('All Core Topics (Balanced Mix)');
  };

  const handleSelectDiscipline = (subj) => {
    onSelectSubject?.(subj.id);
    onSelectUnit?.('');
    onSelectTopic?.('');
    onSelectSubtopic?.('All High-Yield Topics (Balanced Mix)');
  };

  const handleSelectAllTopics = () => {
    onSelectTopic?.('');
    onSelectUnit?.('');
    onSelectSubtopic?.(
      isAllDisciplines
        ? 'All Core Topics (Balanced Mix)'
        : `${activeSubject?.name || 'Discipline'} (All Topics)`
    );
  };

  const handleSelectTopic = (top) => {
    onSelectSubject?.(top.subjectId);
    onSelectUnit?.(top.unitId);
    onSelectTopic?.(top.id, top.name);
    onToggleSubtopic?.('All Core Topics');
  };

  return (
    <div className="wizard-step-column">
      {/* Step Header */}
      <div className="wizard-heading-group">
        <h2 className="wizard-step-title">Exam Section &amp; Topic</h2>
      </div>

      {/* Quick Presets Row */}
      {presets && presets.length > 0 && (
        <div className="wizard-presets-strip">
          <span className="wizard-presets-label">
            <Sparkles size={12} color="var(--brand-primary)" />
            <span>Presets:</span>
          </span>
          <div className="wizard-presets-list">
            {presets.map((preset) => {
              const isMatch = selectedSection === preset.section && totalQuestions === preset.total;
              return (
                <button
                  key={preset.id}
                  type="button"
                  onClick={() => onApplyPreset?.(preset)}
                  className={`wizard-preset-pill ${isMatch ? 'active' : ''}`}
                  title={preset.desc}
                >
                  <span>{preset.label}</span>
                  <span className="wizard-preset-tag">({preset.tag})</span>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Exam Section */}
      <div className="wizard-stacked-decision">
        <div className="wizard-decision-header">
          <span className="wizard-decision-title">Exam Section</span>
        </div>

        <div className="wizard-sections-grid">
          {Object.values(SECTION_METADATA).map((sec) => {
            const Icon = sec.icon;
            const isSelected = selectedSection === sec.id;
            return (
              <div
                key={sec.id}
                className={`wizard-section-card ${isSelected ? 'selected' : ''}`}
                onClick={() => onSelectSection(sec.id)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    onSelectSection(sec.id);
                  }
                }}
                role="button"
                tabIndex={0}
                aria-pressed={isSelected}
              >
                <div className="wizard-section-top">
                  <div className="wizard-section-icon-badge">
                    <Icon size={16} />
                  </div>
                  <div className="wizard-chip-meta">
                    {isSelected && (
                      <CheckCircle2 size={15} color="var(--brand-primary)" />
                    )}
                    <span className="badge-minimal">{sec.tag}</span>
                  </div>
                </div>

                <div className="wizard-section-name">{sec.label}</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Scientific Subject */}
      <div className="wizard-stacked-decision">
        <div className="wizard-decision-header">
          <span className="wizard-decision-title">Subject</span>
        </div>

        <div className="wizard-card-grid">
          {/* Card 1: All Subjects */}
          <div
            className={`wizard-tier-card ${isAllDisciplines ? 'selected' : ''}`}
            onClick={handleSelectAllDisciplines}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                handleSelectAllDisciplines();
              }
            }}
            role="button"
            tabIndex={0}
          >
            <div className="wizard-tier-card-content">
              <div className="wizard-tier-card-title-group">
                <Compass size={15} color="var(--brand-primary)" />
                <span className="wizard-tier-card-title">
                  All Subjects
                </span>
              </div>
              {isAllDisciplines && (
                <CheckCircle2 size={14} color="var(--brand-primary)" />
              )}
            </div>
          </div>

          {/* Cards 2+: Specific Subjects */}
          {subjects.map((subj) => {
            const isSelected = activeSubject?.id === subj.id;
            return (
              <div
                key={subj.id}
                className={`wizard-tier-card ${isSelected ? 'selected' : ''}`}
                onClick={() => handleSelectDiscipline(subj)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    handleSelectDiscipline(subj);
                  }
                }}
                role="button"
                tabIndex={0}
              >
                <div className="wizard-tier-card-content">
                  <div className="wizard-tier-card-title-group">
                    <Atom size={15} color="var(--brand-primary)" />
                    <span className="wizard-tier-card-title">
                      {subj.name}
                    </span>
                  </div>
                  {isSelected && (
                    <CheckCircle2 size={14} color="var(--brand-primary)" />
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Topic Focus */}
      <div className="wizard-stacked-decision">
        <div className="wizard-decision-header">
          <span className="wizard-decision-title">Topic Focus</span>
        </div>

        <div className="wizard-card-grid">
          {/* Card 1: All Topics */}
          <div
            className={`wizard-tier-card ${isAllTopics ? 'selected' : ''}`}
            onClick={handleSelectAllTopics}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                handleSelectAllTopics();
              }
            }}
            role="button"
            tabIndex={0}
          >
            <div className="wizard-tier-card-content">
              <div className="wizard-tier-card-title-group">
                <Layers size={15} color="var(--brand-primary)" />
                <span className="wizard-tier-card-title">
                  All Topics
                </span>
              </div>
              {isAllTopics && (
                <CheckCircle2 size={14} color="var(--brand-primary)" />
              )}
            </div>
          </div>

          {/* Cards 2+: High-Yield Topic Cards */}
          {availableTopics.slice(0, 5).map((top) => {
            const isSelected = activeTopic?.id === top.id;
            return (
              <div
                key={top.id}
                className={`wizard-tier-card ${isSelected ? 'selected' : ''}`}
                onClick={() => handleSelectTopic(top)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    handleSelectTopic(top);
                  }
                }}
                role="button"
                tabIndex={0}
              >
                <div className="wizard-tier-card-content">
                  <div className="wizard-tier-card-title-group">
                    <BookOpen size={14} color="var(--brand-primary)" />
                    <span className="wizard-tier-card-title">
                      {top.name}
                    </span>
                  </div>
                  {isSelected && (
                    <CheckCircle2 size={14} color="var(--brand-primary)" />
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Optional Subtopic Concept Chips if a specific topic is selected */}
        {!isAllTopics && activeTopic && activeTopic.subtopics && activeTopic.subtopics.length > 0 && (
          <div className="wizard-step-fade-enter wizard-subtopics-box">
            <div className="wizard-subtopics-header">
              <span className="wizard-subtopics-label">
                Subtopics:
              </span>
              <span className="badge-minimal">
                {selectedSubtopics.length > 0 ? `${selectedSubtopics.length} Selected` : 'All Concepts'}
              </span>
            </div>
            <div className="wizard-chips-list">
              {/* Chip 0: All Concepts (Default) */}
              <button
                type="button"
                onClick={() => onToggleSubtopic?.('All Core Topics (Balanced Mix)')}
                className={`wizard-filter-chip ${(!selectedSubtopics || selectedSubtopics.length === 0) ? 'active' : ''}`}
              >
                {(!selectedSubtopics || selectedSubtopics.length === 0) && <Check size={11} />}
                <span>All Concepts</span>
              </button>

              {/* Specific Subtopic Chips */}
              {activeTopic.subtopics.map((st) => {
                const isSelected = Boolean(selectedSubtopics?.includes(st));
                return (
                  <button
                    key={st}
                    type="button"
                    onClick={() => {
                      if (onToggleSubtopic) {
                        onToggleSubtopic(st);
                      } else {
                        onSelectSubtopic?.(st);
                      }
                    }}
                    className={`wizard-filter-chip ${isSelected ? 'active' : ''}`}
                  >
                    {isSelected && <Check size={11} />}
                    <span>{st}</span>
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
