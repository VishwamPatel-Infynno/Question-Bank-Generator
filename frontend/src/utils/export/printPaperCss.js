// Print stylesheet for the exam-paper / study-pack HTML document (A4, fixed print colors).
export const PRINT_PAPER_CSS = `
        @page {
          size: A4 portrait;
          margin: 15mm 16mm;
        }
        * {
          box-sizing: border-box;
        }
        body {
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
          color: #0f172a;
          background: #ffffff;
          margin: 0;
          padding: 0;
          font-size: 13px;
          line-height: 1.5;
        }
        .exam-header {
          border-bottom: 2px solid #0f172a;
          padding-bottom: 12px;
          margin-bottom: 20px;
        }
        .header-top {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 12px;
        }
        .brand-title {
          font-size: 18px;
          font-weight: 800;
          letter-spacing: -0.01em;
          color: #0f172a;
          margin: 0 0 2px 0;
        }
        .brand-subtitle {
          font-size: 12px;
          color: #475569;
          font-weight: 500;
          margin: 0;
        }
        .marks-box {
          border: 1.5px solid #0f172a;
          border-radius: 4px;
          padding: 6px 14px;
          text-align: center;
        }
        .marks-label {
          font-size: 10px;
          text-transform: uppercase;
          font-weight: 700;
          color: #64748b;
        }
        .marks-value {
          font-size: 15px;
          font-weight: 800;
          color: #0f172a;
        }
        .candidate-fields {
          display: grid;
          grid-template-columns: 2fr 1fr 1fr;
          gap: 16px;
          background: #f8fafc;
          border: 1px solid #e2e8f0;
          border-radius: 6px;
          padding: 10px 14px;
          font-size: 12px;
        }
        .field-item {
          display: flex;
          align-items: center;
          gap: 6px;
        }
        .field-label {
          font-weight: 700;
          color: #334155;
          white-space: nowrap;
        }
        .field-line {
          flex: 1;
          border-bottom: 1px dotted #94a3b8;
          height: 14px;
        }
        .instructions-bar {
          margin: 12px 0 20px 0;
          padding: 8px 12px;
          background: #eff6ff;
          border-left: 3px solid #3b82f6;
          font-size: 11px;
          color: #1e3a8a;
          border-radius: 0 4px 4px 0;
        }
        .question-block {
          margin-bottom: 24px;
          page-break-inside: avoid;
          border-bottom: 1px solid #e2e8f0;
          padding-bottom: 18px;
        }
        .question-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 8px;
        }
        .question-number {
          font-size: 14px;
          font-weight: 800;
          color: #0f172a;
        }
        .question-meta {
          font-size: 11px;
          color: #64748b;
          font-weight: 600;
        }
        .stimulus-box {
          background: #f8fafc;
          border: 1px solid #e2e8f0;
          border-radius: 6px;
          padding: 12px 14px;
          margin-bottom: 12px;
        }
        .stimulus-title {
          font-size: 11px;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.04em;
          color: #475569;
          margin-bottom: 6px;
        }
        .stimulus-content {
          font-family: Georgia, serif;
          font-size: 12.5px;
          line-height: 1.6;
          color: #1e293b;
          margin: 0 0 8px 0;
        }
        .diagram-box {
          margin: 12px auto;
          text-align: center;
          padding: 10px;
          background: #f8fafc;
          border: 1px solid #e2e8f0;
          border-radius: 6px;
          max-width: 500px;
          page-break-inside: avoid;
        }
        .diagram-box svg, .diagram-box img {
          max-height: 280px;
          max-width: 100%;
          height: auto;
          object-fit: contain;
          display: inline-block;
        }
        .diagram-caption {
          font-size: 11px;
          font-style: italic;
          color: #64748b;
          margin-top: 6px;
          line-height: 1.35;
        }
        .question-stem {
          font-size: 13.5px;
          font-weight: 600;
          color: #0f172a;
          margin: 8px 0 12px 0;
          line-height: 1.45;
        }
        .options-grid {
          display: flex;
          flex-direction: column;
          gap: 6px;
        }
        .option-row {
          display: flex;
          align-items: flex-start;
          gap: 10px;
          padding: 4px 6px;
          border-radius: 4px;
          line-height: 1.45;
        }
        .option-bubble {
          font-family: monospace;
          font-weight: 700;
          color: #94a3b8;
          font-size: 12px;
          white-space: nowrap;
          flex-shrink: 0;
          line-height: 1.45;
        }
        .option-letter {
          font-size: 13px;
          color: #0f172a;
          white-space: nowrap;
          flex-shrink: 0;
          line-height: 1.45;
          min-width: 18px;
        }
        .option-text {
          font-size: 13px;
          color: #1e293b;
          flex: 1;
          line-height: 1.45;
        }
        .page-break {
          page-break-before: always;
          break-before: page;
        }
        .answer-key-section {
          padding-top: 20px;
        }
        .answer-key-header {
          border-bottom: 2px solid #0f172a;
          padding-bottom: 8px;
          margin-bottom: 16px;
        }
        .answer-key-header h2 {
          margin: 0 0 4px 0;
          font-size: 18px;
          font-weight: 800;
        }
        .answer-key-header p {
          margin: 0;
          font-size: 11px;
          color: #64748b;
        }
        .key-table {
          width: 100%;
          border-collapse: collapse;
        }
        .key-table th {
          background: #f1f5f9;
          border: 1px solid #cbd5e1;
          padding: 8px 10px;
          text-align: left;
          font-size: 11px;
          font-weight: 700;
          color: #334155;
          text-transform: uppercase;
        }
        .key-table td {
          border: 1px solid #e2e8f0;
          padding: 8px 10px;
          vertical-align: top;
        }
        .correct-badge {
          display: inline-block;
          background: #10b981;
          color: #ffffff;
          font-weight: 800;
          font-size: 12px;
          padding: 2px 8px;
          border-radius: 4px;
        }
`;
