import { describe, expect, it } from 'vitest';
import {
  getSectionBadgeClass,
  getSectionColor,
  getSectionPacingSeconds,
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
