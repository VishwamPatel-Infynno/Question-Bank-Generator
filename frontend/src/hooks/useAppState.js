/**
 * useAppState - Central application state and handler hook.
 *
 * Extracted from App.jsx to enforce single-responsibility: App.jsx purely
 * assembles the layout while this hook owns all stateful logic, side-effects,
 * and event handlers.
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { useTheme } from './useTheme';
import { useGeneratorForm } from './useGeneratorForm';
import { useKeyboardShortcuts } from './useKeyboardShortcuts';
import { MCAT_SECTIONS_FALLBACK } from '../constants';
import {
  fetchSections,
  fetchHealth,
  startBackgroundBatch,
  fetchBatches,
  fetchQuestionCounts
} from '../services';

/**
 * Central application state hook.
 *
 * Owns all stateful logic, side-effects, and event handlers for the app.
 * App.jsx uses this as its single source of truth - it purely assembles
 * the layout while this hook manages everything stateful.
 *
 * @returns {{
 *   theme: 'light' | 'dark',
 *   toggleTheme: () => void,
 *   activeTab: string,
 *   setActiveTab: (tab: string) => void,
 *   viewMode: 'hero' | 'wizard',
 *   setViewMode: (mode: 'hero' | 'wizard') => void,
 *   wizardStep: number,
 *   setWizardStep: (step: number) => void,
 *   handleNavigateToGenerator: () => void,
 *   handleNavigateToWizard: (step?: number) => void,
 *   handleNavigateToPassages: () => void,
 *   passagesResetSignal: number,
 *   sectionsData: Array<any>,
 *   backendStatus: boolean,
 *   activeBatchCount: number,
 *   generatorForm: ReturnType<typeof useGeneratorForm>,
 *   auditQuestion: any,
 *   setAuditQuestion: (q: any) => void,
 *   toasts: Array<any>,
 *   showToast: (opts: { type?: string, title: string, message?: string, duration?: number }) => void,
 *   dismissToast: (id: string) => void,
 *   handleGenerate: () => void,
 *   handleApplyPreset: (cfg: any) => void,
 *   validatedCount: number,
 *   refreshCounts: () => void,
 *   isLaunchingBatch: boolean
 * }} All app state values and event handler callbacks.
 */
export function useAppState() {
  // ─── Theme ───────────────────────────────────────────────────────────────
  const { theme, toggleTheme } = useTheme();

  // ─── Navigation ──────────────────────────────────────────────────────────
  const [activeTab, setActiveTab] = useState('generator');
  const [viewMode, setViewMode] = useState('hero'); // 'hero' | 'wizard'
  const [wizardStep, setWizardStep] = useState(1);

  // ─── Sections / Backend Status ────────────────────────────────────────────
  const [sectionsData, setSectionsData] = useState([]);
  const [backendStatus, setBackendStatus] = useState(false);
  const [activeBatchCount, setActiveBatchCount] = useState(0);
  const [validatedCount, setValidatedCount] = useState(0);

  // ─── Form ─────────────────────────────────────────────────────────────────
  const generatorForm = useGeneratorForm();
  const { updateFields } = generatorForm;

  // ─── Modals & Background Actions ──────────────────────────────────────────
  const [auditQuestion, setAuditQuestion] = useState(null);
  const [isLaunchingBatch, setIsLaunchingBatch] = useState(false);

  // ─── Toast Notifications ──────────────────────────────────────────────────
  const [toasts, setToasts] = useState([]);

  const showToast = useCallback(({ type = 'info', title, message, duration = 4000 }) => {
    const id = crypto.randomUUID();
    setToasts(prev => [...prev, { id, type, title, message, duration }]);
  }, []);

  const dismissToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  // ─── Navigation Helpers ───────────────────────────────────────────────────
  const handleNavigateToGenerator = useCallback(() => {
    setActiveTab('generator');
    setViewMode('wizard');
    setWizardStep(1);
  }, []);

  const handleNavigateToWizard = useCallback((step = 1) => {
    setActiveTab('generator');
    setViewMode('wizard');
    setWizardStep(step);
  }, []);

  // Passages tab navigation signal to return to catalog even when viewing a passage
  const [passagesResetSignal, setPassagesResetSignal] = useState(0);

  const handleNavigateToPassages = useCallback(() => {
    setActiveTab('passages');
    setPassagesResetSignal((prev) => prev + 1);
  }, []);

  // ─── Bootstrap: Health + Sections ─────────────────────────────────────────
  useEffect(() => {
    fetchHealth()
      .then(() => setBackendStatus(true))
      .catch(() => setBackendStatus(false));

    fetchSections()
      .then((data) => {
        if (data && data.length > 0) {
          setSectionsData(data);
        } else {
          setSectionsData(MCAT_SECTIONS_FALLBACK);
        }
      })
      .catch(() => {
        setSectionsData(MCAT_SECTIONS_FALLBACK);
      });
  }, []);

  // ─── Polling: Active Batch Count + Validated Questions ─────────────────────
  const activeBatchCountRef = useRef(activeBatchCount);
  useEffect(() => {
    activeBatchCountRef.current = activeBatchCount;
  }, [activeBatchCount]);

  const refreshGlobalCounts = useCallback(() => {
    fetchBatches(1, 1)
      .then((data) => {
        setActiveBatchCount(data.active_running_batches || 0);
      })
      .catch(() => {});

    fetchQuestionCounts()
      .then((counts) => {
        setValidatedCount(counts.ai_validated || 0);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    refreshGlobalCounts();

    let timer = null;
    let isCancelled = false;

    const scheduleNext = () => {
      if (isCancelled) return;
      // If there are running background batches, poll every 4s; otherwise idle poll at 30s
      const delay = activeBatchCountRef.current > 0 ? 4000 : 30000;
      timer = setTimeout(() => {
        // No point refreshing counts nobody can see; the visibility handler catches up on return
        if (document.visibilityState !== 'hidden') refreshGlobalCounts();
        scheduleNext();
      }, delay);
    };

    scheduleNext();

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        refreshGlobalCounts();
      }
    };
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      isCancelled = true;
      if (timer) clearTimeout(timer);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [refreshGlobalCounts]);

  // ─── Generate Handler ─────────────────────────────────────────────────────
  const handleGenerate = useCallback(async () => {
    const {
      selectedSection,
      selectedSubject,
      selectedUnit,
      selectedTopic,
      selectedSubtopic,
      selectedSkill,
      selectedSubskill,
      questionType,
      difficulty,
      totalQuestions,
      passageMode,
      passageRequired,
      primaryTrap,
      primaryTraps,
      likelyMistakePattern,
      likelyMistakePatterns,
      customMistakePattern,
      contentDomains,
      contentDomain,
      selectedSubskills,
      selectedSubtopics,
      allowAiImages,
      requireImage,
      additionalInstructions
    } = generatorForm.formData;

    const isVisualsPermitted = Boolean(allowAiImages || requireImage);

    const payload = {
      section: selectedSection,
      subject: selectedSubject || undefined,
      unit: selectedUnit || undefined,
      topic: selectedTopic || undefined,
      subtopic: (selectedSubtopics && selectedSubtopics.length > 0) ? selectedSubtopics.join(', ') : selectedSubtopic,
      aamc_skill: selectedSkill || undefined,
      subskill: (selectedSubskills && selectedSubskills.length > 0) ? selectedSubskills.join(', ') : (selectedSubskill || undefined),
      question_type: questionType || (passageMode === 'single_passage' ? 'PASSAGE_BASED_MCQ' : 'DISCRETE_MCQ'),
      difficulty,
      questions_to_generate: totalQuestions,
      passage_count: passageMode === 'single_passage' ? (totalQuestions === 50 ? 10 : 1) : 0,
      passage_mode: passageMode,
      passage_question_count: passageMode === 'single_passage' ? totalQuestions : undefined,
      interaction_type: 'single_choice',
      passage_required: passageRequired,
      primary_trap: (primaryTraps && primaryTraps.length > 0) ? primaryTraps.join(', ') : (primaryTrap || 'Automatic'),
      likely_mistake_pattern: customMistakePattern || ((likelyMistakePatterns && likelyMistakePatterns.length > 0) ? likelyMistakePatterns.join(', ') : (likelyMistakePattern || 'Automatic')),
      content_domains: contentDomains && contentDomains.length > 0 ? contentDomains : undefined,
      content_domain: contentDomain || (contentDomains && contentDomains.length > 0 ? contentDomains.join(', ') : undefined),
      additional_instructions: additionalInstructions?.trim() || undefined,
      allow_ai_images: isVisualsPermitted,
      require_image: isVisualsPermitted && passageMode !== 'single_passage' && totalQuestions === 1,
      visual_type: isVisualsPermitted ? 'AI_FLUX_Image' : 'None',
      require_passage_image: isVisualsPermitted && passageMode === 'single_passage'
    };

    // Launch background batch generation for both 5 (Quick Set) and 50 (Full Exam) questions
    if (isLaunchingBatch) return;
    setIsLaunchingBatch(true);
    const isQuickSet = totalQuestions === 5;

    try {
      await startBackgroundBatch(payload);
      showToast({
        type: 'success',
        title: isQuickSet ? '5-Question Quick Set Launched' : '50-Question Exam Batch Launched',
        message: isQuickSet
          ? 'Generating 5 practice questions in the background.'
          : 'Generating 50 questions across 10 jobs in the background.'
      });
      setActiveTab('batches');
      refreshGlobalCounts();
    } catch (err) {
      showToast({
        type: 'error',
        title: 'Batch Launch Failed',
        message: err.message || 'Could not launch background batch.'
      });
    } finally {
      setIsLaunchingBatch(false);
    }
  }, [
    generatorForm.formData,
    showToast,
    refreshGlobalCounts,
    isLaunchingBatch
  ]);

  // ─── Preset Handler ───────────────────────────────────────────────────────
  const handleApplyPreset = useCallback((cfg) => {
    updateFields({
      ...(cfg.section && { selectedSection: cfg.section }),
      ...(cfg.difficulty && { difficulty: cfg.difficulty }),
      ...(cfg.totalQuestions !== undefined && { totalQuestions: cfg.totalQuestions }),
      interactionType: 'single_choice',
      ...(cfg.passageCount !== undefined && {
        passageCount: cfg.passageCount,
        passageRequired: cfg.passageCount > 0 ? 'Yes' : 'No'
      }),
      ...(cfg.passageMode && {
        passageMode: cfg.passageMode,
        questionType: cfg.passageMode === 'single_passage' ? 'PASSAGE_BASED_MCQ' : 'DISCRETE_MCQ'
      }),
      ...(cfg.passageQuestionCount !== undefined && { passageQuestionCount: cfg.passageQuestionCount }),
      ...(cfg.primaryTrap && { primaryTrap: cfg.primaryTrap })
    });
    showToast({
      type: 'info',
      title: 'Preset Applied',
      message: `${cfg.totalQuestions || 50} questions configured for ${cfg.section ? cfg.section.replace(/_/g, ' ') : 'MCAT'}.`
    });
  }, [updateFields, showToast]);

  // ─── Keyboard Shortcuts ────────────────────────────────────────────────────
  useKeyboardShortcuts({
    onGenerate: activeTab === 'generator' ? handleGenerate : undefined,
    onToggleTheme: toggleTheme,
    onEscape: () => { if (auditQuestion) setAuditQuestion(null); }
  });

  return {
    // Theme
    theme,
    toggleTheme,
    // Navigation
    activeTab,
    setActiveTab,
    viewMode,
    setViewMode,
    wizardStep,
    setWizardStep,
    handleNavigateToGenerator,
    handleNavigateToWizard,
    handleNavigateToPassages,
    passagesResetSignal,
    // Data
    sectionsData,
    backendStatus,
    activeBatchCount,
    // Form
    generatorForm,
    // Modals
    auditQuestion,
    setAuditQuestion,
    // Toasts
    toasts,
    showToast,
    dismissToast,
    // Handlers
    handleGenerate,
    handleApplyPreset,
    // Counts
    validatedCount,
    refreshCounts: refreshGlobalCounts,
    isLaunchingBatch
  };
}
