import { memo } from 'react';

/**
 * ExportDataFormatPane
 *
 * Renders the tabular spreadsheet (CSV) or structured JSON data format view
 * including the informative educational callout and syntax preview card.
 */
function ExportDataFormatPane({ callout = '', content = '' }) {
  return (
    <div className="exam-export-tab-pane" data-testid="export-data-format-pane">
      {callout && (
        <div className="exam-export-callout" role="note">
          {callout}
        </div>
      )}
      <div className="exam-export-code-preview" tabIndex={0} role="region" aria-label="Export Data Preview">
        {content}
      </div>
    </div>
  );
}

export default memo(ExportDataFormatPane);
