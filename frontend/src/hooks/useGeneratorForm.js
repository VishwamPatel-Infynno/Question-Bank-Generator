import { useState, useCallback } from 'react';
import { toggleSubtopicState } from '../utils/generatorFormState';

const DEFAULT_GENERATOR_FORM = {
  selectedSection: 'chem_phys',
  selectedSubject: '',
  selectedUnit: '',
  selectedTopic: '',
  selectedTopicName: '',
  selectedSubtopic: '',
  selectedSkill: '',
  selectedSubskill: '',
  questionType: 'PASSAGE_BASED_MCQ',
  difficulty: 'medium',
  totalQuestions: 50,
  contentDomains: [],
  contentDomain: '',
  passageCount: 10,
  passageMode: 'single_passage', // 'single_passage' | 'independent'
  passageQuestionCount: 50,
  interactionType: 'single_choice',
  passageRequired: 'Yes',
  primaryTrap: 'Automatic',
  primaryTraps: [],
  likelyMistakePattern: 'Automatic',
  likelyMistakePatterns: [],
  selectedSubskills: [],
  selectedSubtopics: [],
  customMistakePattern: '',
  additionalInstructions: '',
  requireImage: true,
  allowAiImages: true,
  imageMode: 'all', // 'none' | 'all' | 'specific'
  imageQuestionIndices: [], // 1-based question numbers e.g. [1, 2]
  requirePassageImage: true
};

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

  const toggleContentDomain = useCallback((domainId) => {
    setFormData(prev => {
      const current = prev.contentDomains || [];
      const exists = current.includes(domainId);
      const next = exists ? current.filter(d => d !== domainId) : [...current, domainId];
      return {
        ...prev,
        contentDomains: next,
        contentDomain: next.join(', ')
      };
    });
  }, []);

  const toggleQuestionImage = useCallback((qIndex) => {
    setFormData(prev => {
      const current = prev.imageQuestionIndices || [];
      const exists = current.includes(qIndex);
      const next = exists ? current.filter(i => i !== qIndex) : [...current, qIndex].sort((a, b) => a - b);
      const total = prev.totalQuestions || 1;
      let nextMode = 'specific';
      if (next.length === 0 && !prev.requirePassageImage) {
        nextMode = 'none';
      } else if (next.length === total) {
        nextMode = 'all';
      }
      return {
        ...prev,
        imageQuestionIndices: next,
        imageMode: nextMode,
        requireImage: next.length > 0 || prev.requirePassageImage
      };
    });
  }, []);

  const togglePassageImage = useCallback(() => {
    setFormData(prev => {
      const nextPassage = !prev.requirePassageImage;
      const currentIndices = prev.imageQuestionIndices || [];
      return {
        ...prev,
        requirePassageImage: nextPassage,
        requireImage: currentIndices.length > 0 || nextPassage
      };
    });
  }, []);

  const setImageMode = useCallback((mode) => {
    setFormData(prev => {
      const total = prev.totalQuestions || 1;
      if (mode === 'none') {
        return {
          ...prev,
          imageMode: 'none',
          imageQuestionIndices: [],
          requirePassageImage: false,
          requireImage: false
        };
      }
      if (mode === 'all') {
        const allIndices = Array.from({ length: total }, (_, i) => i + 1);
        const isPassage = prev.passageRequired === 'Yes' || prev.passageCount > 0;
        return {
          ...prev,
          imageMode: 'all',
          imageQuestionIndices: allIndices,
          requirePassageImage: isPassage,
          requireImage: true
        };
      }
      // 'specific'
      return {
        ...prev,
        imageMode: 'specific',
        imageQuestionIndices: prev.imageQuestionIndices?.length > 0 ? prev.imageQuestionIndices : [1],
        requireImage: true
      };
    });
  }, []);

  const setImageCount = useCallback((count, candidateIndices = null) => {
    setFormData(prev => {
      const total = prev.totalQuestions || 1;
      const targetList = candidateIndices || Array.from({ length: total }, (_, i) => i + 1);
      const clamped = Math.max(0, Math.min(targetList.length, count));
      const indices = targetList.slice(0, clamped);
      let mode = 'specific';
      if (clamped === 0) mode = 'none';
      else if (clamped === total) mode = 'all';
      return {
        ...prev,
        imageMode: mode,
        imageQuestionIndices: indices,
        requireImage: clamped > 0 || prev.requirePassageImage
      };
    });
  }, []);

  const setRequirePassageImage = useCallback((required) => {
    setFormData(prev => {
      const currentIndices = prev.imageQuestionIndices || [];
      return {
        ...prev,
        requirePassageImage: Boolean(required),
        requireImage: currentIndices.length > 0 || Boolean(required)
      };
    });
  }, []);

  const resetForm = useCallback((overrides = {}) => {
    setFormData({
      ...DEFAULT_GENERATOR_FORM,
      ...overrides
    });
  }, []);

  const setGenerationTotal = useCallback((total) => {
    const validTotal = total === 5 ? 5 : 50;
    setFormData(prev => {
      const isPassage = prev.passageMode === 'single_passage';
      return {
        ...prev,
        totalQuestions: validTotal,
        passageCount: isPassage ? (validTotal === 50 ? 10 : 1) : 0,
        passageQuestionCount: isPassage ? validTotal : 0,
        imageQuestionIndices: (prev.imageQuestionIndices || []).filter(idx => idx <= validTotal)
      };
    });
  }, []);

  const setAllowAiImages = useCallback((allowed) => {
    const val = Boolean(allowed);
    setFormData(prev => ({
      ...prev,
      allowAiImages: val,
      requireImage: val,
      requirePassageImage: val,
      imageMode: val ? 'all' : 'none'
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
      const current = prev.primaryTraps || [];
      const exists = current.includes(trapId);
      const next = exists ? current.filter(t => t !== trapId) : [...current, trapId];
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
      const current = prev.selectedSubskills || [];
      const exists = current.includes(subskill);
      const next = exists ? current.filter(s => s !== subskill) : [...current, subskill];
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
      const current = prev.likelyMistakePatterns || [];
      const exists = current.includes(patternId);
      const next = exists ? current.filter(p => p !== patternId) : [...current, patternId];
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
    setFormData,
    updateField,
    updateFields,
    toggleContentDomain,
    toggleQuestionImage,
    togglePassageImage,
    togglePrimaryTrap,
    toggleSubskill,
    toggleMistakePattern,
    toggleSubtopic,
    setImageMode,
    setImageCount,
    setRequirePassageImage,
    setAllowAiImages,
    resetForm,
    setGenerationTotal
  };
}

