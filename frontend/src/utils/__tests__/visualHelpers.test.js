import { describe, expect, it } from 'vitest';
import { detectVisualModality, getModalityMetadata } from '../visualHelpers';

describe('visualHelpers', () => {
  describe('detectVisualModality', () => {
    it('prefers explicit visual_medical_category or image_modality from question', () => {
      expect(detectVisualModality({ visual_medical_category: 'Radiology' })).toBe('radiology');
      expect(detectVisualModality({ image_modality: 'Histology' })).toBe('histology');
    });

    it('prefers stage_outcomes modality over regex scanning', () => {
      const q = {
        stage_outcomes: {
          visual_stimulus: { modality: 'cellular_microscopy' }
        },
        question_stem: 'A chest X-ray shows consolidation.'
      };
      expect(detectVisualModality(q)).toBe('cellular_microscopy');
    });

    it('detects radiology from description or question stem', () => {
      expect(
        detectVisualModality(null, 'Axial CT scan slice of the thoracic cavity')
      ).toBe('radiology');
      expect(
        detectVisualModality({ question_stem: 'A chest film reveals an opacity in the right upper lobe.' })
      ).toBe('radiology');
    });

    it('detects histology from description or question stem', () => {
      expect(
        detectVisualModality(null, 'High-power H&E stained slide showing glomeruli and tubular epithelium')
      ).toBe('histology');
      expect(
        detectVisualModality({ question_stem: 'A biopsy of the striated muscle reveals sarcomere disruption.' })
      ).toBe('histology');
    });

    it('detects gross anatomy from description or stem', () => {
      expect(
        detectVisualModality(null, 'Anatomical dissection of the circle of Willis at the base of the brain')
      ).toBe('gross_anatomy');
    });

    it('detects cellular electron microscopy from description or stem', () => {
      expect(
        detectVisualModality(null, 'Transmission electron microscopy (TEM) micrograph showing cilia axoneme 9+2 arrangement')
      ).toBe('cellular_microscopy');
    });

    it('detects physiology traces from description or stem', () => {
      expect(
        detectVisualModality(null, 'Lead II ECG rhythm strip displaying delta waves and shortened PR interval')
      ).toBe('physiology_trace');
    });

    it('detects clinical pathology photographs from description or stem', () => {
      expect(
        detectVisualModality(null, 'Clinical photograph of a pigmented skin lesion with asymmetrical borders (melanoma)')
      ).toBe('clinical_pathology');
    });

    it('falls back to svg_diagram when isSvg is true and no pattern matches', () => {
      expect(detectVisualModality(null, 'Reaction pathway coordinate diagram', true)).toBe('svg_diagram');
    });

    it('falls back to scientific_diagram when not svg and no pattern matches', () => {
      expect(detectVisualModality(null, 'Lineweaver-Burk double reciprocal plot', false)).toBe('scientific_diagram');
    });
  });

  describe('getModalityMetadata', () => {
    it('returns appropriate styling and dark container flag for radiology', () => {
      const meta = getModalityMetadata('radiology');
      expect(meta.label).toBe('Radiology (X-Ray / CT / MRI)');
      expect(meta.badgeClass).toBe('badge-cyan');
      expect(meta.isDarkContainer).toBe(true);
    });

    it('returns appropriate styling for histology', () => {
      const meta = getModalityMetadata('histology');
      expect(meta.label).toBe('Histopathology (H&E)');
      expect(meta.badgeClass).toBe('badge-purple');
      expect(meta.isDarkContainer).toBe(false);
    });

    it('returns appropriate styling for electron microscopy', () => {
      const meta = getModalityMetadata('cellular_microscopy');
      expect(meta.label).toBe('Electron Microscopy (TEM/SEM)');
      expect(meta.badgeClass).toBe('badge-indigo');
      expect(meta.isDarkContainer).toBe(true);
    });

    it('returns appropriate styling for physiology traces', () => {
      const meta = getModalityMetadata('physiology_trace');
      expect(meta.label).toBe('Physiology / ECG Trace');
      expect(meta.badgeClass).toBe('badge-rose');
      expect(meta.isDarkContainer).toBe(false);
    });

    it('returns appropriate styling for SVG diagrams', () => {
      const meta = getModalityMetadata('svg_diagram');
      expect(meta.label).toBe('SVG Vector Diagram');
      expect(meta.badgeClass).toBe('badge-purple');
      expect(meta.isDarkContainer).toBe(false);
    });

    it('returns fallback styling for unknown modalities', () => {
      expect(getModalityMetadata('unknown', true).label).toBe('SVG Vector Diagram');
      expect(getModalityMetadata('unknown', false).label).toBe('Scientific Figure');
      expect(getModalityMetadata('unknown', false).badgeClass).toBe('badge-neutral');
      expect(getModalityMetadata('unknown', false).isDarkContainer).toBe(false);
    });
  });
});
