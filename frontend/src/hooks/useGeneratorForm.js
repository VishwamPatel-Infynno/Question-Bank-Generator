import { SECTION_IDS, DIFFICULTY } from '../constants';
import { useState, useCallback } from 'react';
import { toggleInList, toggleSubtopicState } from '../utils/generatorFormState';

const DEFAULT_GENERATOR_FORM = {
  selectedSection: SECTION_IDS.CHEM_PHYS,
  selectedSubject: '',
  selectedUnit: '',
  selectedTopic: '',
  selectedTopicName: '',
  selectedSubtopic: '',
  selectedSkill: '',
  selectedSubskill: '',
  questionType: 'PASSAGE_BASED_MCQ',
  difficulty: DIFFICULTY.MEDIUM,
  totalQuestions: 50,
  passageMode: 'single_passage', // 'single_passage' | 'independent'
  passageRequired: 'Yes',
  primaryTrap: 'Automatic',
  primaryTraps: [],
  likelyMistakePattern: 'Automatic',
  likelyMistakePatterns: [],
  selectedSubskills: [],
  selectedSubtopics: [],
  additionalInstructions: '',
  requireImage: true,
  allowAiImages: true,
  requirePassageImage: true
};

/**
 * Manages the multi-step question-generation form state.
 *
 * @param {Partial<typeof DEFAULT_GENERATOR_FORM>} [initialValues] - Optional overrides for the default form values.
 * @returns {{
 *   formData: typeof DEFAULT_GENERATOR_FORM,
 *   updateField: (key: string, value: any) => void,
 *   updateFields: (fields: Partial<typeof DEFAULT_GENERATOR_FORM>) => void,
 *   setGenerationTotal: (total: 5 | 50) => void,
 *   setAllowAiImages: (allowed: boolean) => void,
 *   togglePrimaryTrap: (trapId: string) => void,
 *   toggleSubskill: (subskill: string) => void,
 *   toggleMistakePattern: (patternId: string) => void,
 *   toggleSubtopic: (subtopic: string) => void,
 * }}
 */
export function useGeneratorForm(initialValues = {}) {
  const [formData, setFormData] = useState(() => ({
    ...DEFAULT_GENERATOR_FORM,
    ...initialValues
  }));

  const updateField = useCallback((key, value) => {
    setFormData(prev => ({
      ...prev,
      [key]: value
    }));
  }, []);

  const updateFields = useCallback((fieldsObj) => {
    setFormData(prev => ({
      ...prev,
      ...fieldsObj
    }));
  }, []);

  const setGenerationTotal = useCallback((total) => {
    setFormData(prev => ({ ...prev, totalQuestions: total === 5 ? 5 : 50 }));
  }, []);

  const setAllowAiImages = useCallback((allowed) => {
    const val = Boolean(allowed);
    setFormData(prev => ({
      ...prev,
      allowAiImages: val,
      requireImage: val,
      requirePassageImage: val
    }));
  }, []);

  const togglePrimaryTrap = useCallback((trapId) => {
    setFormData(prev => {
      if (trapId === 'Automatic') {
        return {
          ...prev,
          primaryTraps: [],
          primaryTrap: 'Automatic'
        };
      }
      const next = toggleInList(prev.primaryTraps, trapId);
      return {
        ...prev,
        primaryTraps: next,
        primaryTrap: next.length === 0 ? 'Automatic' : next.join(', ')
      };
    });
  }, []);

  const toggleSubskill = useCallback((subskill) => {
    setFormData(prev => {
      if (subskill === 'All' || subskill === 'Automatic' || subskill === '') {
        return {
          ...prev,
          selectedSubskills: [],
          selectedSubskill: ''
        };
      }
      const next = toggleInList(prev.selectedSubskills, subskill);
      return {
        ...prev,
        selectedSubskills: next,
        selectedSubskill: next.join(', ')
      };
    });
  }, []);

  const toggleMistakePattern = useCallback((patternId) => {
    setFormData(prev => {
      if (patternId === 'Automatic' || patternId === 'None') {
        return {
          ...prev,
          likelyMistakePatterns: [],
          likelyMistakePattern: patternId
        };
      }
      const next = toggleInList(prev.likelyMistakePatterns, patternId);
      return {
        ...prev,
        likelyMistakePatterns: next,
        likelyMistakePattern: next.length === 0 ? 'Automatic' : next.join(', ')
      };
    });
  }, []);

  const toggleSubtopic = useCallback((subtopic) => {
    setFormData((prev) => toggleSubtopicState(prev, subtopic));
  }, []);

  return {
    formData,
    updateField,
    updateFields,
    togglePrimaryTrap,
    toggleSubskill,
    toggleMistakePattern,
    toggleSubtopic,
    setAllowAiImages,
    setGenerationTotal
  };
}

