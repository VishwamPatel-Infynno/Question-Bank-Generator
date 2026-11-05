import { FlaskConical, BookOpen, Dna, Brain } from 'lucide-react';
// Bundled manager taxonomy JSON provides zero-latency offline-first fallback
// synchronized with backend/app/data/mcat_dependent_taxonomy.json
import mcatTaxonomy from './mcat_dependent_taxonomy.json';

/**
 * Single source of truth for the four MCAT sections. Every other section map (labels, badge
 * classes, colors, codes, pacing) is derived from this table so a value is written exactly once.
 * Colors are hex on purpose: some consumers append an alpha suffix (e.g. `${color}15`).
 */
const SECTIONS = {
  chem_phys: {
    code: 'CP',
    label: 'Chemical and Physical Foundations',
    badge: 'badge-cyan',
    color: '#38bdf8',
    pacingSeconds: 96,
    pacing: { target: '~96s / question', desc: '59 questions in 95 mins' }
  },
  cars: {
    code: 'CARS',
    label: 'Critical Analysis and Reasoning Skills',
    badge: 'badge-rose',
    color: '#f43f5e',
    pacingSeconds: 101,
    pacing: { target: '~101s / question', desc: '53 questions in 90 mins' }
  },
  bio_biochem: {
    code: 'BB',
    label: 'Biological and Biochemical Foundations',
    badge: 'badge-emerald',
    color: '#10b981',
    pacingSeconds: 96,
    pacing: { target: '~96s / question', desc: '59 questions in 95 mins' }
  },
  psych_soc: {
    code: 'PS',
    label: 'Psychological, Social, and Biological Foundations',
    badge: 'badge-purple',
    color: '#a855f7',
    pacingSeconds: 96,
    pacing: { target: '~96s / question', desc: '59 questions in 95 mins' }
  }
};

const NEUTRAL_SECTION_COLOR = '#94a3b8';
const SECTION_CODE_TO_ID = Object.fromEntries(
  Object.entries(SECTIONS).map(([id, sec]) => [sec.code, id])
);

/** Builds a map keyed by BOTH the long id (chem_phys) and the short code (CP). */
function keyedByIdAndCode(pick) {
  return Object.fromEntries(
    Object.entries(SECTIONS).flatMap(([id, sec]) => [
      [id, pick(sec)],
      [sec.code, pick(sec)]
    ])
  );
}

/**
 * Resolves a section id, short code, or legacy label to a canonical id (chem_phys, cars,
 * bio_biochem, psych_soc), or null when it cannot be recognized.
 */
export function normalizeSectionId(section) {
  if (!section) return null;
  if (SECTIONS[section]) return section;
  if (SECTION_CODE_TO_ID[section]) return SECTION_CODE_TO_ID[section];
  const s = String(section).toLowerCase();
  if (s.includes('chem') || s.includes('cp')) return 'chem_phys';
  if (s.includes('cars')) return 'cars';
  if (s.includes('bio') || s.includes('bb')) return 'bio_biochem';
  if (s.includes('psych') || s.includes('ps')) return 'psych_soc';
  return null;
}

export const PACING_INFO = keyedByIdAndCode((sec) => sec.pacing);
export const SECTION_CODE_MAP = keyedByIdAndCode((sec) => sec.code);
export const MCAT_SECTION_LABELS = keyedByIdAndCode((sec) => sec.label);

export function getSectionBadgeClass(section) {
  const id = normalizeSectionId(section);
  return id ? SECTIONS[id].badge : 'badge-neutral';
}

export function getSectionColor(section) {
  const id = normalizeSectionId(section);
  return id ? SECTIONS[id].color : NEUTRAL_SECTION_COLOR;
}

/** Seconds per question used for exam-time estimates (96 when the section is unknown). */
export function getSectionPacingSeconds(section) {
  const id = normalizeSectionId(section);
  return id ? SECTIONS[id].pacingSeconds : 96;
}

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
  const code = SECTION_CODE_MAP[sectionIdOrCode] || String(sectionIdOrCode).toUpperCase();
  return (mcatTaxonomy.sections || []).find((s) => s.id === code) || null;
}

export function getSubjectsForSection(sectionIdOrCode) {
  const sec = getSectionTree(sectionIdOrCode);
  return sec?.subjects || [];
}

export function getSkillsForSection(sectionIdOrCode) {
  const code = SECTION_CODE_MAP[sectionIdOrCode] || String(sectionIdOrCode).toUpperCase();
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

/**
 * Score cut-offs (exclusive) used when a question has no explicit status. They mirror the
 * backend's PASSING_SCORE_THRESHOLD (90) and BATCH_PASSING_SCORE_THRESHOLD (85); keep one copy
 * here so the review queue and the batch views never disagree.
 */
export const SCORE_CUTOFFS = Object.freeze({ aiValidatedAbove: 90, batchAbove: 85 });
