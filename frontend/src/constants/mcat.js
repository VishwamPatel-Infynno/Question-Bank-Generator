import { FlaskConical, BookOpen, Dna, Brain } from 'lucide-react';
// Bundled manager taxonomy JSON provides zero-latency offline-first fallback
// synchronized with backend/app/data/mcat_dependent_taxonomy.json
import mcatTaxonomy from './mcat_dependent_taxonomy.json';

export const PACING_INFO = {
  chem_phys: { target: '~96s / question', desc: '59 questions in 95 mins' },
  cars: { target: '~101s / question', desc: '53 questions in 90 mins' },
  bio_biochem: { target: '~96s / question', desc: '59 questions in 95 mins' },
  psych_soc: { target: '~96s / question', desc: '59 questions in 95 mins' },
  CP: { target: '~96s / question', desc: '59 questions in 95 mins' },
  CARS: { target: '~101s / question', desc: '53 questions in 90 mins' },
  BB: { target: '~96s / question', desc: '59 questions in 95 mins' },
  PS: { target: '~96s / question', desc: '59 questions in 95 mins' }
};

const SECTION_ID_TO_CODE = {
  chem_phys: 'CP',
  cars: 'CARS',
  bio_biochem: 'BB',
  psych_soc: 'PS',
  CP: 'CP',
  CARS: 'CARS',
  BB: 'BB',
  PS: 'PS'
};

const SECTION_CODE_TO_ID = {
  CP: 'chem_phys',
  CARS: 'cars',
  BB: 'bio_biochem',
  PS: 'psych_soc',
  chem_phys: 'chem_phys',
  cars: 'cars',
  bio_biochem: 'bio_biochem',
  psych_soc: 'psych_soc'
};

export const SECTION_CODE_MAP = SECTION_ID_TO_CODE;

const SECTION_BADGE_CLASSES = {
  chem_phys: 'badge-cyan',
  cars: 'badge-rose',
  bio_biochem: 'badge-emerald',
  psych_soc: 'badge-purple',
  CP: 'badge-cyan',
  CARS: 'badge-rose',
  BB: 'badge-emerald',
  PS: 'badge-purple'
};

export function getSectionBadgeClass(section) {
  if (!section) return 'badge-neutral';
  return SECTION_BADGE_CLASSES[section] || SECTION_BADGE_CLASSES[SECTION_CODE_TO_ID[section]] || 'badge-neutral';
}

const SECTION_COLORS = {
  chem_phys: '#38bdf8',
  cars: '#f43f5e',
  bio_biochem: '#10b981',
  psych_soc: '#a855f7',
  CP: '#38bdf8',
  CARS: '#f43f5e',
  BB: '#10b981',
  PS: '#a855f7'
};

export function getSectionColor(section) {
  if (!section) return '#94a3b8';
  if (SECTION_COLORS[section]) return SECTION_COLORS[section];
  const normalized = SECTION_CODE_TO_ID[section];
  if (normalized && SECTION_COLORS[normalized]) return SECTION_COLORS[normalized];
  const s = String(section).toLowerCase();
  if (s.includes('chem') || s.includes('cp')) return '#38bdf8';
  if (s.includes('cars')) return '#f43f5e';
  if (s.includes('bio') || s.includes('bb')) return '#10b981';
  if (s.includes('psych') || s.includes('ps')) return '#a855f7';
  return '#94a3b8';
}

export const MCAT_SECTION_LABELS = {
  chem_phys: 'Chemical and Physical Foundations',
  cars: 'Critical Analysis and Reasoning Skills',
  bio_biochem: 'Biological and Biochemical Foundations',
  psych_soc: 'Psychological, Social, and Biological Foundations',
  CP: 'Chemical and Physical Foundations',
  CARS: 'Critical Analysis and Reasoning Skills',
  BB: 'Biological and Biochemical Foundations',
  PS: 'Psychological, Social, and Biological Foundations'
};

/**
 * Builds fallback sections list with aggregated subtopics.
 */
export const MCAT_SECTIONS_FALLBACK = (mcatTaxonomy.sections || []).map((sec) => {
  const code = sec.id;
  const id = SECTION_CODE_TO_ID[code] || code.toLowerCase();
  const subtopics = [];
  (sec.subjects || []).forEach((subj) => {
    (subj.units || []).forEach((unit) => {
      (unit.topics || []).forEach((topic) => {
        (topic.subtopics || []).forEach((st) => {
          subtopics.push(st);
        });
      });
    });
  });

  return {
    id,
    code,
    label: sec.name,
    shortLabel: code === 'CP' ? 'Chem / Phys' : code === 'BB' ? 'Bio / Biochem' : code === 'PS' ? 'Psych / Soc' : 'CARS',
    subtopics,
    subjects: sec.subjects || []
  };
});

/**
 * All 25 Primary Traps with Automatic option.
 */
export const COGNITIVE_TRAPS = [
  { id: 'Automatic', label: 'Automatic (Recommended)', desc: 'Selects the most realistic AAMC trap for this question type.' },
  ...(mcatTaxonomy.generation_options?.primary_trap || []).map((t) => ({
    id: t.id,
    label: t.value,
    desc: `Targets ${t.value.toLowerCase()} in answer analysis.`
  }))
];

/**
 * 24 Likely Mistake Patterns from manager taxonomy.
 */
export const LIKELY_MISTAKE_PATTERNS = (mcatTaxonomy.generation_options?.likely_mistake_pattern?.values || []).map((m) => ({
  id: m.id,
  label: m.value
}));

function getSectionTree(sectionIdOrCode) {
  const code = SECTION_ID_TO_CODE[sectionIdOrCode] || String(sectionIdOrCode).toUpperCase();
  return (mcatTaxonomy.sections || []).find((s) => s.id === code) || null;
}

export function getSubjectsForSection(sectionIdOrCode) {
  const sec = getSectionTree(sectionIdOrCode);
  return sec?.subjects || [];
}

export function getSkillsForSection(sectionIdOrCode) {
  const code = SECTION_ID_TO_CODE[sectionIdOrCode] || String(sectionIdOrCode).toUpperCase();
  return (mcatTaxonomy.skills || []).filter((sk) => (sk.applies_to || []).includes(code));
}

export const SECTION_METADATA = {
  chem_phys: {
    id: 'chem_phys',
    label: 'Chemical and Physical Foundations',
    shortCode: 'CP',
    icon: FlaskConical,
    tag: 'Chemistry & Physics',
    color: '#0284c7',
    desc: 'Chemistry, physics, thermodynamics, and math applied to biological systems.',
    coachTip: '⚡ MCAT Coach Tip: Check units and estimate orders of magnitude before doing exact arithmetic to save time!'
  },
  cars: {
    id: 'cars',
    label: 'Critical Analysis and Reasoning Skills',
    shortCode: 'CARS',
    icon: BookOpen,
    tag: 'Critical Reasoning',
    color: '#e11d48',
    desc: 'Passage analysis, logic, and arguments in humanities and social sciences with no outside knowledge needed.',
    coachTip: '⚡ MCAT Coach Tip: Rely only on what is in the passage. Every correct answer is anchored solely in the text and author’s argument.'
  },
  bio_biochem: {
    id: 'bio_biochem',
    label: 'Biological and Biochemical Foundations',
    shortCode: 'BB',
    icon: Dna,
    tag: 'Biology & Biochem',
    color: '#059669',
    desc: 'Biology, biochemistry, enzyme pathways, genetics, and cell physiology experiments.',
    coachTip: '⚡ MCAT Coach Tip: Study graphs and experiment controls first before reading the question prompt.'
  },
  psych_soc: {
    id: 'psych_soc',
    label: 'Psychological, Social, and Biological Foundations',
    shortCode: 'PS',
    icon: Brain,
    tag: 'Behavioral Sciences',
    color: '#7c3aed',
    desc: 'Psychology, sociology, behavior, and social factors in health.',
    coachTip: '⚡ MCAT Coach Tip: Pay close attention to subtle differences between similar theories (e.g., Conflict Theory vs. Functionalism).'
  }
};

export const DIFFICULTY_TIERS = [
  {
    id: 'low',
    title: 'Easy',
    desc: 'Core science concepts and straightforward questions.',
    color: '#10b981',
    badgeClass: 'badge-emerald'
  },
  {
    id: 'medium',
    title: 'Medium',
    desc: 'Standard exam difficulty and multi-step reasoning.',
    color: '#f59e0b',
    badgeClass: 'badge-amber'
  },
  {
    id: 'high',
    title: 'Hard',
    desc: 'Challenging questions with multi-step logic and complex data.',
    color: '#f43f5e',
    badgeClass: 'badge-rose'
  }
];

export const formatDifficulty = (diff) => {
  const d = (diff || '').toLowerCase();
  if (d === 'low' || d === 'easy') return 'Easy';
  if (d === 'high' || d === 'hard') return 'Hard';
  return 'Medium';
};

export const getDifficultyBadgeClass = (diff) => {
  const d = (diff || '').toLowerCase();
  if (d === 'low' || d === 'easy') return 'badge-emerald';
  if (d === 'high' || d === 'hard') return 'badge-rose';
  return 'badge-amber';
};

export * from './mcatTraps';
