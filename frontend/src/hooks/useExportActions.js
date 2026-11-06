import { useMemo } from 'react';
import { generateExamCsv, generateExamJson, generateExamHtmlDoc } from '../utils/export';
import { downloadTextFile } from '../utils/download';
import { useCopyToClipboard } from './useCopyToClipboard';

const FORMATS = {
  csv: {
    label: 'CSV',
    build: generateExamCsv,
    mime: 'text/csv;charset=utf-8;',
    options: { bom: true }
  },
  json: {
    label: 'JSON',
    build: generateExamJson,
    mime: 'application/json;charset=utf-8;',
    options: {}
  }
};

/**
 * Download, copy and print actions of the export dialog, with their toasts.
 *
 * @param {Object} args
 * @param {Array<object>} args.questions - Questions being exported
 * @param {'student'|'studypack'} args.paperMode - Print layout
 * @param {(toast: object) => void} [args.onShowToast]
 */
export function useExportActions({ questions, paperMode, onShowToast }) {
  const { copiedKey, copy } = useCopyToClipboard();
  const toast = (payload) => {
    if (onShowToast) onShowToast(payload);
  };

  const content = useMemo(
    () => ({
      csv: FORMATS.csv.build(questions),
      json: FORMATS.json.build(questions)
    }),
    [questions]
  );

  const download = (kind) => {
    const { label, mime, options } = FORMATS[kind];
    if (!content[kind]) return;
    downloadTextFile(
      content[kind],
      `mcat_exam_${questions.length}_questions.${kind}`,
      mime,
      options
    );
    toast({
      type: 'success',
      title: `${label} Exported`,
      message: `Successfully downloaded ${label} for ${questions.length} questions.`
    });
  };

  const copyToClipboard = async (kind) => {
    const { label } = FORMATS[kind];
    if (!content[kind]) return;
    const ok = await copy(content[kind], kind);
    if (ok) {
      toast({ type: 'success', title: 'Copied to Clipboard', message: `${label} data copied.` });
    } else {
      // Clipboard needs HTTPS and permission; say so instead of failing silently
      toast({
        type: 'error',
        title: 'Copy Failed',
        message: 'The browser blocked clipboard access. Use Download instead.'
      });
    }
  };

  // Opens the print-ready paper in a new window (Print / Save as PDF)
  const printPaper = () => {
    if (!questions || questions.length === 0) return;
    const printWindow = window.open('', '_blank');
    if (!printWindow) {
      toast({
        type: 'error',
        title: 'Pop-up Blocked',
        message: 'Please allow pop-ups for this site to print or save as PDF.'
      });
      return;
    }
    printWindow.document.open();
    printWindow.document.write(generateExamHtmlDoc(questions, { paperMode }));
    printWindow.document.close();
  };

  return {
    csvContent: content.csv,
    jsonContent: content.json,
    copiedCsv: copiedKey === 'csv',
    copiedJson: copiedKey === 'json',
    handleDownloadCsv: () => download('csv'),
    handleCopyCsv: () => copyToClipboard('csv'),
    handleDownloadJson: () => download('json'),
    handleCopyJson: () => copyToClipboard('json'),
    handleNativePrint: printPaper
  };
}

