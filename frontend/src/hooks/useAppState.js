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
import {
  startBackgroundBatch,
  fetchBatches,
  fetchQuestionCounts
} from '../services';
import { makeId } from '../utils/ids';
import { applySectionRules } from '../utils/generatorFormState';
import { buildBatchPayload } from '../utils';

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
 *   backendStatus: boolean | null,  (null while the first check is pending)
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
  // null = still connecting, true = online, false = offline
  const [backendStatus, setBackendStatus] = useState(null);
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
    const id = makeId();
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


  // ─── Polling: Active Batch Count + Validated Questions ─────────────────────
  const activeBatchCountRef = useRef(activeBatchCount);
  useEffect(() => {
    activeBatchCountRef.current = activeBatchCount;
  }, [activeBatchCount]);

  const countsAbortRef = useRef(null);

  // Optionally takes counts the caller already fetched so they are not requested a second time.
  const refreshGlobalCounts = useCallback((prefetchedCounts) => {
    countsAbortRef.current?.abort();
    const controller = new AbortController();
    countsAbortRef.current = controller;
    const { signal } = controller;

    // limit: 1 keeps the payload tiny; active_running_batches is counted over the whole table
    fetchBatches({ limit: 1 }, signal)
      .then((data) => {
        setActiveBatchCount(data.active_running_batches || 0);
        setBackendStatus(true);
      })
      .catch((err) => {
        // This poll doubles as the health check, so the navbar recovers and goes offline live
        if (err?.name !== 'AbortError') setBackendStatus(false);
      });

    if (prefetchedCounts && typeof prefetchedCounts === 'object' && 'ai_validated' in prefetchedCounts) {
      Promise.resolve(prefetchedCounts).then((counts) => {
        setValidatedCount(counts.ai_validated || 0);
      });
      return;
    }
    fetchQuestionCounts(signal)
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
      countsAbortRef.current?.abort();
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [refreshGlobalCounts]);

  // ─── Generate Handler ─────────────────────────────────────────────────────
  const handleGenerate = useCallback(async () => {
    const payload = buildBatchPayload(generatorForm.formData);
    const { totalQuestions } = generatorForm.formData;

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
      ...(cfg.section &&
        applySectionRules(generatorForm.formData, cfg.section, cfg.totalQuestions)),
      ...(cfg.difficulty && { difficulty: cfg.difficulty }),
      ...(cfg.totalQuestions !== undefined && { totalQuestions: cfg.totalQuestions }),
      ...(cfg.passageCount !== undefined && { passageRequired: cfg.passageCount > 0 ? 'Yes' : 'No' }),
      ...(cfg.passageMode && {
        passageMode: cfg.passageMode,
        questionType: cfg.passageMode === 'single_passage' ? 'PASSAGE_BASED_MCQ' : 'DISCRETE_MCQ'
      }),
      ...(cfg.primaryTrap && { primaryTrap: cfg.primaryTrap })
    });
    showToast({
      type: 'info',
      title: 'Preset Applied',
      message: `${cfg.totalQuestions || 50} questions configured for ${cfg.section ? cfg.section.replace(/_/g, ' ') : 'MCAT'}.`
    });
  }, [updateFields, showToast, generatorForm.formData]);

  // ─── Keyboard Shortcuts ────────────────────────────────────────────────────
  useKeyboardShortcuts({
    // Only on the wizard's final review step: elsewhere the shortcut would silently launch a
    // full batch with whatever defaults the form holds.
    onGenerate:
      activeTab === 'generator' && viewMode === 'wizard' && wizardStep === 3
        ? handleGenerate
        : undefined,
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
