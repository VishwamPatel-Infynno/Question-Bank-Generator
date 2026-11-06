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
    shortLabel: 'Chem / Phys',
    label: 'Chemical and Physical Foundations',
    badge: 'badge-cyan',
    color: '#38bdf8',
    pacingSeconds: 96,
    pacing: { target: '~96s / question', desc: '59 questions in 95 mins' }
  },
  cars: {
    code: 'CARS',
    shortLabel: 'CARS',
    label: 'Critical Analysis and Reasoning Skills',
    badge: 'badge-rose',
    color: '#f43f5e',
    pacingSeconds: 101,
    pacing: { target: '~101s / question', desc: '53 questions in 90 mins' }
  },
  bio_biochem: {
    code: 'BB',
    shortLabel: 'Bio / Biochem',
    label: 'Biological and Biochemical Foundations',
    badge: 'badge-emerald',
    color: '#10b981',
    pacingSeconds: 96,
    pacing: { target: '~96s / question', desc: '59 questions in 95 mins' }
  },
  psych_soc: {
    code: 'PS',
    shortLabel: 'Psych / Soc',
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
  const s = String(section).toLowerCase().trim();
  // Order matters: the Psych/Soc label contains "biological" and the Bio/Biochem label contains
  // "chem", so the more specific sections are tested before chem_phys.
  if (/\bcars\b|critical analysis/.test(s)) return 'cars';
  if (/psych|social|behavio|^ps(bb)?$/.test(s)) return 'psych_soc';
  if (/biochem|\bbio\b|^bb(ls)?$/.test(s)) return 'bio_biochem';
  if (/chem|physic|^cp(bs)?$/.test(s)) return 'chem_phys';
  return null;
}

export const PACING_INFO = keyedByIdAndCode((sec) => sec.pacing);
export const SECTION_CODE_MAP = keyedByIdAndCode((sec) => sec.code);
export const MCAT_SECTION_LABELS = keyedByIdAndCode((sec) => sec.label);

/** The four exam section ids as used in form state, filters and the API. */
export const SECTION_IDS = Object.freeze({
  CHEM_PHYS: 'chem_phys',
  CARS: 'cars',
  BIO_BIOCHEM: 'bio_biochem',
  PSYCH_SOC: 'psych_soc'
});

/** Short section name for pills and table badges ("Chem / Phys"), the id itself when unknown. */
export function getSectionShortLabel(section) {
  const id = normalizeSectionId(section);
  return (id && SECTIONS[id]?.shortLabel) || section || 'General';
}

/** Section filter pills: "All Sections" plus one per exam section. */
export const SECTION_FILTER_OPTIONS = Object.freeze([
  { id: '', label: 'All Sections' },
  ...Object.entries(SECTIONS).map(([id, sec]) => ({ id, label: sec.shortLabel }))
]);

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
    shortLabel: SECTIONS[id]?.shortLabel || code,
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
    desc: 'Chemistry, physics, thermodynamics, and math applied to biological systems.',
    coachTip: '⚡ MCAT Coach Tip: Check units and estimate orders of magnitude before doing exact arithmetic to save time!'
  },
  cars: {
    id: 'cars',
    label: 'Critical Analysis and Reasoning Skills',
    shortCode: 'CARS',
    icon: BookOpen,
    tag: 'Critical Reasoning',
    desc: 'Passage analysis, logic, and arguments in humanities and social sciences with no outside knowledge needed.',
    coachTip: '⚡ MCAT Coach Tip: Rely only on what is in the passage. Every correct answer is anchored solely in the text and author’s argument.'
  },
  bio_biochem: {
    id: 'bio_biochem',
    label: 'Biological and Biochemical Foundations',
    shortCode: 'BB',
    icon: Dna,
    tag: 'Biology & Biochem',
    desc: 'Biology, biochemistry, enzyme pathways, genetics, and cell physiology experiments.',
    coachTip: '⚡ MCAT Coach Tip: Study graphs and experiment controls first before reading the question prompt.'
  },
  psych_soc: {
    id: 'psych_soc',
    label: 'Psychological, Social, and Biological Foundations',
    shortCode: 'PS',
    icon: Brain,
    tag: 'Behavioral Sciences',
    desc: 'Psychology, sociology, behavior, and social factors in health.',
    coachTip: '⚡ MCAT Coach Tip: Pay close attention to subtle differences between similar theories (e.g., Conflict Theory vs. Functionalism).'
  }
};

export const DIFFICULTY_TIERS = [
  {
    id: 'low',
    title: 'Easy',
    desc: 'Core science concepts and straightforward questions.',
    badgeClass: 'badge-emerald'
  },
  {
    id: 'medium',
    title: 'Medium',
    desc: 'Standard exam difficulty and multi-step reasoning.',
    badgeClass: 'badge-amber'
  },
  {
    id: 'high',
    title: 'Hard',
    desc: 'Challenging questions with multi-step logic and complex data.',
    badgeClass: 'badge-rose'
  }
];

/** The three difficulty levels the UI works with (the API/DB also stores easy/hard aliases). */
export const DIFFICULTY = Object.freeze({ LOW: 'low', MEDIUM: 'medium', HIGH: 'high' });

const DIFFICULTY_ALIASES = Object.freeze({
  low: DIFFICULTY.LOW,
  easy: DIFFICULTY.LOW,
  medium: DIFFICULTY.MEDIUM,
  standard: DIFFICULTY.MEDIUM,
  high: DIFFICULTY.HIGH,
  hard: DIFFICULTY.HIGH
});

/**
 * Canonical level ('low' | 'medium' | 'high') for any stored spelling (case-insensitive, with the
 * easy/hard/standard aliases), or null for empty or unknown input.
 */
export function normalizeDifficulty(diff) {
  return DIFFICULTY_ALIASES[String(diff ?? '').trim().toLowerCase()] ?? null;
}

const DIFFICULTY_LABELS = { low: 'Easy', medium: 'Medium', high: 'Hard' };
const DIFFICULTY_BADGES = { low: 'badge-emerald', medium: 'badge-amber', high: 'badge-rose' };

export const formatDifficulty = (diff) =>
  DIFFICULTY_LABELS[normalizeDifficulty(diff) ?? DIFFICULTY.MEDIUM];

export const getDifficultyBadgeClass = (diff) =>
  DIFFICULTY_BADGES[normalizeDifficulty(diff) ?? DIFFICULTY.MEDIUM];


/**
 * Score cut-offs (exclusive) used when a question has no explicit status. They mirror the
 * backend's PASSING_SCORE_THRESHOLD (90) and BATCH_PASSING_SCORE_THRESHOLD (85); keep one copy
 * here so the review queue and the batch views never disagree.
 */
export const SCORE_CUTOFFS = Object.freeze({ aiValidatedAbove: 90, batchAbove: 85 });

/** Batch lifecycle statuses as the API returns them (mirrors backend BatchStatus). */
export const BATCH_STATUS = Object.freeze({
  PENDING: 'pending',
  IN_PROGRESS: 'in_progress',
  RUNNING: 'running',
  COMPLETED: 'completed',
  PARTIALLY_COMPLETED: 'partially_completed',
  FAILED: 'failed',
  CANCELLED: 'cancelled',
  STOPPED: 'stopped'
});

/** Values of the batch list's status filter tabs (a view concern: 'all' is not a status). */
export const BATCH_FILTER = Object.freeze({
  ALL: 'all',
  RUNNING: BATCH_STATUS.IN_PROGRESS,
  COMPLETED: BATCH_STATUS.COMPLETED,
  FAILED: BATCH_STATUS.FAILED
});

/** Job lifecycle statuses (mirrors backend JobStatus). */
export const JOB_STATUS = Object.freeze({
  PENDING: 'pending',
  RUNNING: 'running',
  COMPLETED: 'completed',
  FAILED: 'failed',
  CANCELLED: 'cancelled',
  STOPPED: 'stopped'
});

/** Question lifecycle statuses (mirrors backend QuestionStatus). */
export const QUESTION_STATUS = Object.freeze({
  IN_BANK: 'in_bank',
  AI_VALIDATED: 'ai_validated',
  BATCH_ONLY: 'batch_only',
  BELOW_THRESHOLD: 'below_threshold',
  DISCARDED: 'discarded',
  DELETED: 'deleted'
});

/** True for a batch or job that was halted (stopped by the user or cancelled). */
export const isStoppedStatus = (status) =>
  status === BATCH_STATUS.STOPPED || status === BATCH_STATUS.CANCELLED;

export const EMPTY_ARRAY = Object.freeze([]);
export const EMPTY_OBJECT = Object.freeze({});
