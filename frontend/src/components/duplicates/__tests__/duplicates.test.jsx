// @vitest-environment jsdom
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { DuplicateRiskBadge, DuplicateAlertBar, DuplicateCompareModal } from '..';

const info = (over = {}) => ({
  is_duplicate: true,
  similarity_score: 0.88,
  matched_question_id: 'orig',
  matched_question_stem: 'Which organelle makes ATP?',
  matched_options: [
    { id: 'A', text: 'Nucleus' },
    { id: 'B', text: 'Mitochondrion' }
  ],
  matched_explanation: 'The **mitochondrion** makes ATP.',
  match_reason: 'Same stem and key',
  is_overridden: false,
  overridden_at: null,
  ...over
});

const question = (infoOver, extra = {}) => ({
  id: 'q1',
  question_stem: 'Where is ATP made?',
  options: [
    { id: 'A', text: 'Cell nucleus' },
    { id: 'B', text: 'Powerhouse' }
  ],
  correct_answer_id: 'B',
  explanation: 'Because energy.',
  duplicate_info: info(infoOver),
  ...extra
});

let container;
let root;

beforeEach(() => {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
});

const render = (node) => act(() => root.render(node));
const click = (el) => act(() => el.dispatchEvent(new MouseEvent('click', { bubbles: true })));

describe('DuplicateRiskBadge', () => {
  it('renders nothing without a duplicate signal', () => {
    render(<DuplicateRiskBadge question={{ id: 'x' }} />);
    expect(container.innerHTML).toBe('');
    render(<DuplicateRiskBadge question={question({ is_duplicate: false, similarity_score: 0.3 })} />);
    expect(container.innerHTML).toBe('');
  });

  it('shows the three labels with their tones', () => {
    render(<DuplicateRiskBadge question={question()} />);
    expect(container.textContent).toBe('Duplicate Risk (88%)');
    expect(container.querySelector('.badge-rose')).not.toBeNull();

    render(<DuplicateRiskBadge question={question({ is_duplicate: false, similarity_score: 0.65 })} />);
    expect(container.textContent).toBe('Similar (65%)');
    expect(container.querySelector('.badge-amber')).not.toBeNull();

    render(<DuplicateRiskBadge question={question({ is_overridden: true })} />);
    expect(container.textContent).toBe('Overridden');
    expect(container.querySelector('.badge-emerald.overridden')).not.toBeNull();
  });

  it('is a labelled button only when onClick is given, and passes the question', () => {
    const q = question();
    render(<DuplicateRiskBadge question={q} />);
    expect(container.querySelector('button')).toBeNull();

    const onClick = vi.fn();
    render(<DuplicateRiskBadge question={q} onClick={onClick} />);
    const btn = container.querySelector('button');
    expect(btn.getAttribute('aria-label')).toContain('Duplicate Risk (88%)');
    click(btn);
    expect(onClick).toHaveBeenCalledWith(q);
  });
});

describe('DuplicateAlertBar', () => {
  it('renders an alert with the reason and both actions', () => {
    const q = question();
    const onCompare = vi.fn();
    const onOverride = vi.fn();
    render(<DuplicateAlertBar question={q} onCompare={onCompare} onOverride={onOverride} />);
    const bar = container.querySelector('[role="alert"]');
    expect(bar).not.toBeNull();
    expect(bar.textContent).toContain('88%');
    expect(bar.textContent).toContain('Same stem and key');

    const buttons = [...container.querySelectorAll('button')];
    click(buttons.find((b) => b.textContent.includes('Compare')));
    click(buttons.find((b) => b.textContent.includes('Override and approve')));
    expect(onCompare).toHaveBeenCalledWith(q);
    expect(onOverride).toHaveBeenCalledWith(q);
  });

  it('disables the override button while overriding', () => {
    render(<DuplicateAlertBar question={question()} onOverride={() => {}} isOverriding />);
    expect(container.querySelector('button').disabled).toBe(true);
  });

  it('shows a calm note, not an alert, once overridden', () => {
    render(<DuplicateAlertBar question={question({ is_overridden: true })} onOverride={() => {}} />);
    expect(container.querySelector('[role="alert"]')).toBeNull();
    expect(container.querySelector('[role="status"]')).not.toBeNull();
    expect(container.querySelector('button')).toBeNull();
  });

  it('renders nothing for a question with no duplicate signal', () => {
    render(<DuplicateAlertBar question={{ id: 'x' }} />);
    expect(container.innerHTML).toBe('');
  });
});

describe('DuplicateCompareModal', () => {
  afterEach(() => {
    document.body.innerHTML = '';
    container = document.createElement('div');
    document.body.appendChild(container);
  });

  const text = () => document.body.textContent;

  it('renders nothing when there is no question', () => {
    render(<DuplicateCompareModal question={null} onClose={() => {}} />);
    expect(document.querySelector('[role="dialog"]')).toBeNull();
  });

  it('shows this question and the original side by side with the key on the left', () => {
    render(<DuplicateCompareModal question={question()} onClose={() => {}} onOverride={() => {}} />);
    expect(document.querySelector('[role="dialog"][aria-modal="true"]')).not.toBeNull();
    expect(text()).toContain('Where is ATP made?');
    expect(text()).toContain('Which organelle makes ATP?');
    expect(text()).toContain('Mitochondrion');
    expect(text()).toContain('88% similar');
    // Bold markers are formatted, never left raw or injected as HTML
    expect(document.querySelector('.dup-compare-explanation strong')?.textContent).toBe('mitochondrion');
    const keys = document.querySelectorAll('.dup-compare-option.correct');
    expect(keys.length).toBe(1);
    expect(keys[0].textContent).toContain('Powerhouse');
  });

  it('falls back when the original is gone', () => {
    const q = question({ matched_question_stem: null, matched_options: null, matched_explanation: null });
    render(<DuplicateCompareModal question={q} onClose={() => {}} />);
    expect(text()).toContain('The original is no longer available');
  });

  it('has Close and Override in the footer; override passes the question', () => {
    const q = question();
    const onClose = vi.fn();
    const onOverride = vi.fn();
    render(<DuplicateCompareModal question={q} onClose={onClose} onOverride={onOverride} />);
    const footer = [...document.querySelectorAll('.modal-footer button')];
    click(footer.find((b) => b.textContent.trim() === 'Close'));
    click(footer.find((b) => b.textContent.includes('Override and approve')));
    expect(onClose).toHaveBeenCalled();
    expect(onOverride).toHaveBeenCalledWith(q);
  });

  it('hides Override once the question is already overridden', () => {
    render(<DuplicateCompareModal question={question({ is_overridden: true })} onClose={() => {}} onOverride={() => {}} />);
    expect(document.querySelector('.modal-footer').textContent).not.toContain('Override and approve');
  });
});
