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
import {
  getSubjectsForSection
} from '../../../constants';

const EMPTY_OBJECT = Object.freeze({});
const EMPTY_ARRAY = Object.freeze([]);

export default function WizardStep1SectionFocus({
  selectedSection = 'chem_phys',
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

  // Gather available topics
  const availableTopics = useMemo(() => {
    if (activeSubject) {
      const res = [];
      (activeSubject.units || []).forEach((u) => {
        (u.topics || []).forEach((t) => {
          res.push({
            ...t,
            unitId: u.id,
            unitName: u.name,
            subjectId: activeSubject.id,
            subjectName: activeSubject.name
          });
        });
      });
      return res;
    }

    // When All Disciplines is selected, gather the primary high-yield topics across the section
    const res = [];
    subjects.forEach((s) => {
      (s.units || []).forEach((u, uIdx) => {
        if (uIdx < 2) {
          (u.topics || []).forEach((t, tIdx) => {
            if (tIdx < 2) {
              res.push({
                ...t,
                unitId: u.id,
                unitName: u.name,
                subjectId: s.id,
                subjectName: s.name
              });
            }
          });
        }
      });
    });
    return res;
  }, [subjects, activeSubject]);

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
    onSelectTopic?.(top.id);
    onSelectSubtopic?.(top.name);
    if (onToggleSubtopic) {
      onToggleSubtopic('All Core Topics');
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Step Header */}
      <div className="wizard-heading-group">
        <h2 className="wizard-step-title">Exam Section &amp; Topic</h2>
      </div>

      {/* Quick Presets Row */}
      {presets && presets.length > 0 && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            flexWrap: 'wrap',
            padding: '8px 12px',
            borderRadius: 'var(--radius-sm)',
            background: 'var(--bg-surface-subtle)',
            border: '1px solid var(--border-light)',
            fontSize: '0.75rem'
          }}
        >
          <span style={{ fontWeight: 600, color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Sparkles size={12} color="var(--brand-primary)" />
            <span>Presets:</span>
          </span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap', flex: 1 }}>
            {presets.map((preset) => {
              const isMatch = selectedSection === preset.section && totalQuestions === preset.total;
              return (
                <button
                  key={preset.id}
                  type="button"
                  onClick={() => onApplyPreset?.(preset)}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '5px',
                    padding: '3px 10px',
                    borderRadius: 'var(--radius-full)',
                    background: isMatch ? 'var(--brand-light)' : 'var(--bg-surface)',
                    border: isMatch ? '1px solid var(--border-brand)' : '1px solid var(--border-light)',
                    color: isMatch ? 'var(--brand-primary)' : 'var(--text-secondary)',
                    fontWeight: isMatch ? 600 : 500,
                    fontSize: '0.72rem',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                  title={preset.desc}
                >
                  <span>{preset.label}</span>
                  <span style={{ fontSize: '0.65rem', opacity: 0.75 }}>({preset.tag})</span>
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
                  <div
                    className="wizard-section-icon-badge"
                    style={{
                      background: isSelected ? 'var(--brand-primary)' : 'var(--bg-surface-hover)',
                      color: isSelected ? 'var(--text-on-brand)' : 'var(--text-secondary)'
                    }}
                  >
                    <Icon size={16} />
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    {isSelected && (
                      <CheckCircle2 size={15} style={{ color: 'var(--brand-primary)' }} />
                    )}
                    <span className="badge-minimal" style={{ fontSize: '0.68rem' }}>{sec.tag}</span>
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

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '10px' }}>
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
            style={{ padding: '12px 14px' }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Compass size={15} style={{ color: 'var(--brand-primary)' }} />
                <span style={{ fontSize: '0.86rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                  All Subjects
                </span>
              </div>
              {isAllDisciplines && (
                <CheckCircle2 size={14} style={{ color: 'var(--brand-primary)' }} />
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
                style={{ padding: '12px 14px' }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Atom size={15} style={{ color: 'var(--brand-primary)' }} />
                    <span style={{ fontSize: '0.86rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {subj.name}
                    </span>
                  </div>
                  {isSelected && (
                    <CheckCircle2 size={14} style={{ color: 'var(--brand-primary)' }} />
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

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '10px' }}>
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
            style={{ padding: '12px 14px' }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Layers size={15} style={{ color: 'var(--brand-primary)' }} />
                <span style={{ fontSize: '0.86rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                  All Topics
                </span>
              </div>
              {isAllTopics && (
                <CheckCircle2 size={14} style={{ color: 'var(--brand-primary)' }} />
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
                style={{ padding: '12px 14px' }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <BookOpen size={14} style={{ color: 'var(--brand-primary)' }} />
                    <span style={{ fontSize: '0.86rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {top.name}
                    </span>
                  </div>
                  {isSelected && (
                    <CheckCircle2 size={14} style={{ color: 'var(--brand-primary)' }} />
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Optional Subtopic Concept Chips if a specific topic is selected */}
        {!isAllTopics && activeTopic && activeTopic.subtopics && activeTopic.subtopics.length > 0 && (
          <div
            className="wizard-step-fade-enter"
            style={{
              marginTop: '12px',
              padding: '12px 14px',
              borderRadius: 'var(--radius-sm)',
              background: 'var(--bg-surface-subtle)',
              border: '1px solid var(--border-light)'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px', flexWrap: 'wrap', gap: '6px' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
                Subtopics:
              </span>
              <span className="badge-minimal" style={{ fontSize: '0.68rem' }}>
                {selectedSubtopics.length > 0 ? `${selectedSubtopics.length} Selected` : 'All Concepts'}
              </span>
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
              {/* Chip 0: All Concepts (Default) */}
              <button
                type="button"
                onClick={() => {
                  onSelectSubtopic?.(`${activeTopic.name} (All Concepts)`);
                  if (onToggleSubtopic) {
                    onToggleSubtopic('All Core Topics (Balanced Mix)');
                  }
                }}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '5px',
                  padding: '4px 10px',
                  borderRadius: 'var(--radius-full)',
                  background: (!selectedSubtopics || selectedSubtopics.length === 0) ? 'var(--brand-primary)' : 'var(--bg-surface)',
                  border: (!selectedSubtopics || selectedSubtopics.length === 0) ? '1px solid var(--brand-primary)' : '1px solid var(--border-light)',
                  color: (!selectedSubtopics || selectedSubtopics.length === 0) ? 'var(--text-on-brand)' : 'var(--text-secondary)',
                  fontSize: '0.72rem',
                  fontWeight: (!selectedSubtopics || selectedSubtopics.length === 0) ? 600 : 500,
                  cursor: 'pointer',
                  transition: 'all 0.12s ease'
                }}
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
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '5px',
                      padding: '4px 10px',
                      borderRadius: 'var(--radius-full)',
                      background: isSelected ? 'var(--brand-primary)' : 'var(--bg-surface)',
                      border: isSelected ? '1px solid var(--brand-primary)' : '1px solid var(--border-light)',
                      color: isSelected ? 'var(--text-on-brand)' : 'var(--text-secondary)',
                      fontSize: '0.72rem',
                      fontWeight: isSelected ? 600 : 500,
                      cursor: 'pointer',
                      transition: 'all 0.12s ease'
                    }}
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
