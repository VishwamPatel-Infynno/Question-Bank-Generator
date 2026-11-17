import { DIFFICULTY } from '../../constants';

/**
 * wizardConstants.js - Configuration steps and quick presets for GuidedWizard.
 */

export const STEP_CONFIG = [
  { num: 1, label: 'Section & Topic', short: 'Section', subtitle: 'Choose Exam Section & Topic', nextLabel: 'Continue' },
  { num: 2, label: 'Difficulty & Format', short: 'Format', subtitle: 'Choose Difficulty & Format', nextLabel: 'Review & Create' },
  { num: 3, label: 'Review & Create', short: 'Review', subtitle: 'Review & Start Generation', nextLabel: 'Create Questions' }
];

export const QUICK_PRESETS = [
  {
    id: 'bio_biochem_5',
    label: 'Biochem Passage Set',
    tag: '5 Qs',
    section: 'bio_biochem',
    total: 5,
    passageRequired: 'Yes',
    passageMode: 'single_passage',
    desc: 'Enzyme kinetics & metabolic regulation passage'
  },
  {
    id: 'cars_essay_5',
    label: 'CARS Reasoning',
    tag: '5 Qs',
    section: 'cars',
    total: 5,
    passageRequired: 'Yes',
    passageMode: 'single_passage',
    desc: 'Humanities & social sciences reasoning passage'
  },
  {
    id: 'chem_phys_5',
    label: 'Physics Standalone',
    tag: '5 Qs',
    section: 'chem_phys',
    total: 5,
    passageRequired: 'No',
    passageMode: 'independent',
    desc: 'Discrete physics & chemistry questions'
  },
  {
    id: 'psych_soc_5',
    label: 'Psych / Sociology',
    tag: '5 Qs',
    section: 'psych_soc',
    total: 5,
    passageRequired: 'Yes',
    passageMode: 'single_passage',
    desc: 'Cognitive bias & behavioral health study'
  }
];

export const HERO_PRESETS = Object.freeze([
  {
    label: 'Chem / Phys',
    sectionId: 'chem_phys',
    config: {
      section: 'chem_phys',
      difficulty: DIFFICULTY.MEDIUM,
      totalQuestions: 50,
      passageMode: 'single_passage',
      passageQuestionCount: 50,
      passageCount: 10,
      passageRequired: 'Yes'
    }
  },
  {
    label: 'CARS',
    sectionId: 'cars',
    config: {
      section: 'cars',
      difficulty: DIFFICULTY.MEDIUM,
      totalQuestions: 50,
      passageCount: 10,
      passageMode: 'single_passage',
      passageQuestionCount: 50,
      passageRequired: 'Yes'
    }
  },
  {
    label: 'Bio / Biochem',
    sectionId: 'bio_biochem',
    config: {
      section: 'bio_biochem',
      difficulty: DIFFICULTY.HIGH,
      totalQuestions: 50,
      passageMode: 'single_passage',
      passageQuestionCount: 50,
      passageCount: 10,
      passageRequired: 'Yes'
    }
  },
  {
    label: 'Psych / Soc',
    sectionId: 'psych_soc',
    config: {
      section: 'psych_soc',
      difficulty: DIFFICULTY.MEDIUM,
      totalQuestions: 50,
      passageMode: 'independent',
      passageQuestionCount: 0,
      passageCount: 0,
      passageRequired: 'No'
    }
  }
]);


