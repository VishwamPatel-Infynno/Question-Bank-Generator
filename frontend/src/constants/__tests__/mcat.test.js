import { describe, expect, it } from 'vitest';
import {
  AAMC_REASONING_SKILLS,
  DIFFICULTY,
  formatAamcSkill,
  formatDifficulty,
  getDifficultyBadgeClass,
  getSectionBadgeClass,
  getSectionColor,
  getSectionPacingSeconds,
  normalizeDifficulty,
  normalizeSectionId
} from '../mcat';

describe('normalizeSectionId', () => {
  it('accepts canonical ids and short codes', () => {
    expect(normalizeSectionId('chem_phys')).toBe('chem_phys');
    expect(normalizeSectionId('CP')).toBe('chem_phys');
    expect(normalizeSectionId('CARS')).toBe('cars');
    expect(normalizeSectionId('BB')).toBe('bio_biochem');
    expect(normalizeSectionId('PS')).toBe('psych_soc');
  });

  it('accepts the backend long codes in any case', () => {
    expect(normalizeSectionId('CPBS')).toBe('chem_phys');
    expect(normalizeSectionId('bbls')).toBe('bio_biochem');
    expect(normalizeSectionId('PSBB')).toBe('psych_soc');
  });

  it('resolves the full AAMC section names to the right section', () => {
    expect(normalizeSectionId('Chemical and Physical Foundations of Biological Systems')).toBe('chem_phys');
    expect(normalizeSectionId('Critical Analysis and Reasoning Skills')).toBe('cars');
    // contain "chem" / "bio" but belong to the Bio/Biochem and Psych/Soc sections
    expect(normalizeSectionId('Biological and Biochemical Foundations of Living Systems')).toBe('bio_biochem');
    expect(normalizeSectionId('Psychological, Social, and Biological Foundations of Behavior')).toBe('psych_soc');
  });

  it('returns null for empty or unknown input', () => {
    expect(normalizeSectionId('')).toBeNull();
    expect(normalizeSectionId(null)).toBeNull();
    expect(normalizeSectionId('astronomy')).toBeNull();
  });
});

describe('section helpers', () => {
  it('derive badge, color and pacing from the normalised id', () => {
    expect(getSectionBadgeClass('Biological and Biochemical Foundations of Living Systems')).toBe('badge-emerald');
    expect(getSectionColor('PS')).toBe('#a855f7');
    expect(getSectionPacingSeconds('CARS')).toBe(101);
  });

  it('fall back for unknown sections', () => {
    expect(getSectionBadgeClass('nope')).toBe('badge-neutral');
    expect(getSectionColor('nope')).toBe('#94a3b8');
    expect(getSectionPacingSeconds('nope')).toBe(96);
  });
});

describe('normalizeDifficulty', () => {
  it.each([
    ['low', DIFFICULTY.LOW],
    ['EASY', DIFFICULTY.LOW],
    [' Medium ', DIFFICULTY.MEDIUM],
    ['standard', DIFFICULTY.MEDIUM],
    ['High', DIFFICULTY.HIGH],
    ['hard', DIFFICULTY.HIGH]
  ])('maps %s to %s', (input, expected) => {
    expect(normalizeDifficulty(input)).toBe(expected);
  });

  it('returns null for empty or unknown input', () => {
    for (const bad of ['', null, undefined, 'expert']) expect(normalizeDifficulty(bad)).toBeNull();
  });
});

describe('difficulty display helpers', () => {
  it('label and badge every alias consistently', () => {
    expect(formatDifficulty('easy')).toBe('Easy');
    expect(formatDifficulty('low')).toBe('Easy');
    expect(formatDifficulty('hard')).toBe('Hard');
    expect(getDifficultyBadgeClass('hard')).toBe('badge-rose');
    expect(getDifficultyBadgeClass('LOW')).toBe('badge-emerald');
  });

  it('treat unknown levels as medium', () => {
    expect(formatDifficulty('???')).toBe('Medium');
    expect(getDifficultyBadgeClass(undefined)).toBe('badge-amber');
  });
});

describe('formatAamcSkill', () => {
  it('has valid dictionary entries for official skills', () => {
    expect(Object.keys(AAMC_REASONING_SKILLS).length).toBeGreaterThan(0);
    expect(AAMC_REASONING_SKILLS.Skill_2).toBe('Scientific Reasoning and Problem-Solving');
  });

  it('maps raw internal codes to exact human-readable AAMC reasoning skill names', () => {
    expect(formatAamcSkill('Skill_1')).toBe('Knowledge of Scientific Concepts and Principles');
    expect(formatAamcSkill('Skill_2')).toBe('Scientific Reasoning and Problem-Solving');
    expect(formatAamcSkill('Skill_3')).toBe('Reasoning About Research Design and Execution');
    expect(formatAamcSkill('Skill_4')).toBe('Data-Based and Statistical Reasoning');
    expect(formatAamcSkill('CARS_Skill_1')).toBe('Foundations of Comprehension');
    expect(formatAamcSkill('CARS_Skill_2')).toBe('Reasoning Within the Text');
    expect(formatAamcSkill('CARS_Skill_3')).toBe('Reasoning Beyond the Text');
  });

  it('supports space-separated and short code aliases', () => {
    expect(formatAamcSkill('Skill 2')).toBe('Scientific Reasoning and Problem-Solving');
    expect(formatAamcSkill('S2')).toBe('Scientific Reasoning and Problem-Solving');
    expect(formatAamcSkill('CARS2')).toBe('Reasoning Within the Text');
  });

  it('handles null, undefined, empty, and fallback gracefully', () => {
    expect(formatAamcSkill('')).toBe('');
    expect(formatAamcSkill(null)).toBe('');
    expect(formatAamcSkill(undefined, 'Fallback')).toBe('Fallback');
    expect(formatAamcSkill('Custom Skill Name')).toBe('Custom Skill Name');
  });
});
