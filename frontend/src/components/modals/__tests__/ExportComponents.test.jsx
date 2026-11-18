// @vitest-environment jsdom
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import ExportScopeSelector from '../ExportScopeSelector';
import ExportDataFormatPane from '../ExportDataFormatPane';

describe('ExportScopeSelector', () => {
  let container;
  let root;

  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    container.remove();
  });

  it('renders all scope buttons when selected and filtered are available', () => {
    act(() => {
      root.render(
        <ExportScopeSelector
          scope="selected"
          onScopeChange={() => {}}
          exportCount={5}
          selectedCount={5}
          filteredCount={10}
          allCount={50}
          hasActiveFilters={true}
        />
      );
    });

    const selector = container.querySelector('[data-testid="export-scope-selector"]');
    expect(selector).not.toBeNull();
    expect(container.textContent).toContain('Questions (5)');
    expect(container.textContent).toContain('Selected (5)');
    expect(container.textContent).toContain('Filtered (10)');
    expect(container.textContent).toContain('All (50)');

    const activeBtn = container.querySelector('.pill-track-btn.active');
    expect(activeBtn?.textContent).toContain('Selected (5)');
  });

  it('calls onScopeChange when clicking a scope button', () => {
    const handleScopeChange = vi.fn();
    act(() => {
      root.render(
        <ExportScopeSelector
          scope="all"
          onScopeChange={handleScopeChange}
          exportCount={50}
          selectedCount={0}
          filteredCount={0}
          allCount={50}
          hasActiveFilters={false}
        />
      );
    });

    const allBtn = container.querySelector('.pill-track-btn.active');
    expect(allBtn?.textContent).toContain('All (50)');
    act(() => {
      allBtn?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });
    expect(handleScopeChange).toHaveBeenCalledWith('all');
  });

  it('hides filtered button when hasActiveFilters is false', () => {
    act(() => {
      root.render(
        <ExportScopeSelector
          scope="all"
          onScopeChange={() => {}}
          exportCount={50}
          selectedCount={0}
          filteredCount={15}
          allCount={50}
          hasActiveFilters={false}
        />
      );
    });

    expect(container.textContent).not.toContain('Filtered');
  });
});

describe('ExportDataFormatPane', () => {
  let container;
  let root;

  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    container.remove();
  });

  it('renders callout and syntax preview content', () => {
    act(() => {
      root.render(
        <ExportDataFormatPane
          callout="Exports clean spreadsheet for Excel"
          content="id,stem,answer"
        />
      );
    });

    const pane = container.querySelector('[data-testid="export-data-format-pane"]');
    expect(pane).not.toBeNull();
    expect(container.textContent).toContain('Exports clean spreadsheet for Excel');
    expect(container.textContent).toContain('id,stem,answer');
  });
});
