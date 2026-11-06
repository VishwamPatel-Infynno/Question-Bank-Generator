import { describe, it, expect } from 'vitest';
import { getQuestionVisual, hasQuestionImage } from '../questionHelpers';
import {
  applySectionRules,
  defaultSubtopicLabel,
  toggleSubtopicState
} from '../generatorFormState';

describe('getQuestionVisual', () => {
  it('prefers the question\'s own figure, then the image stage, then the shared passage figure', () => {
    const own = { image_svg: '<svg/>', image_description: 'own' };
    expect(getQuestionVisual(own)).toEqual({ svg: '<svg/>', url: '', description: 'own' });

    const staged = {
      stage_outcomes: { visual_stimulus: { image_url: 'https://x/1.png', image_description: 'staged' } }
    };
    expect(getQuestionVisual(staged)).toEqual({ svg: '', url: 'https://x/1.png', description: 'staged' });

    const passage = {
      stage_outcomes: { passage_visual_stimulus: { image_url: 'https://x/p.png', image_description: 'passage' } }
    };
    expect(getQuestionVisual(passage).url).toBe('https://x/p.png');
    expect(getQuestionVisual(passage).description).toBe('passage');
    expect(hasQuestionImage(passage)).toBe(true);
  });

  it('is empty for a question without any figure', () => {
    expect(getQuestionVisual({})).toEqual({ svg: '', url: '', description: '' });
    expect(getQuestionVisual(null)).toEqual({ svg: '', url: '', description: '' });
    expect(hasQuestionImage({ stage_outcomes: { visual_stimulus: { image_description: 'text only' } } })).toBe(false);
  });
});

describe('subtopic labels use the topic name, not its id', () => {
  const form = { selectedTopic: 'ATOMIC_PARTICLES', selectedTopicName: 'Atomic Structure', selectedSubtopics: [] };

  it('defaultSubtopicLabel reads the display name', () => {
    expect(defaultSubtopicLabel(form)).toBe('Atomic Structure (All Concepts)');
    expect(defaultSubtopicLabel({ selectedTopic: '' })).toBe('All High-Yield Topics (Balanced Mix)');
  });

  it('a reset value clears the list and relabels from the name', () => {
    const next = toggleSubtopicState({ ...form, selectedSubtopics: ['Isotopes'] }, 'All Core Topics');
    expect(next.selectedSubtopics).toEqual([]);
    expect(next.selectedSubtopic).toBe('Atomic Structure (All Concepts)');
  });
});

describe('applySectionRules', () => {
  it('CARS is passage-only with no figures', () => {
    const next = applySectionRules({ totalQuestions: 20 }, 'cars');
    expect(next.selectedSection).toBe('cars');
    expect(next.allowAiImages).toBe(false);
    expect(next.requireImage).toBe(false);
    expect(next.passageMode).toBe('single_passage');
    expect(next.passageQuestionCount).toBe(20);
    expect(next.selectedSkill).toMatch(/^CARS/);
  });

  it('a science section re-enables AI figures and resets the topic selection', () => {
    const next = applySectionRules({ selectedTopic: 'X', totalQuestions: 10 }, 'chem_phys');
    expect(next.allowAiImages).toBe(true);
    expect(next.selectedTopic).toBe('');
    expect(next.selectedTopicName).toBe('');
    expect(next.selectedSubtopic).toBe('All Core Topics (Balanced Mix)');
  });
});
