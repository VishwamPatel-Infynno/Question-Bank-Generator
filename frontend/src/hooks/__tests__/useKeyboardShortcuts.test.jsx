// @vitest-environment jsdom
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useKeyboardShortcuts } from '../useKeyboardShortcuts';

function Harness(props) {
  useKeyboardShortcuts(props);
  return null;
}

let root;
let container;
beforeEach(() => {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
});
afterEach(() => {
  act(() => root.unmount());
  container.remove();
  document.body.innerHTML = '';
});

const mount = (props) => act(() => root.render(<Harness {...props} />));
const press = (key, init = {}, target = window) => {
  const event = new KeyboardEvent('keydown', { key, bubbles: true, cancelable: true, ...init });
  act(() => {
    target.dispatchEvent(event);
  });
  return event;
};

describe('useKeyboardShortcuts', () => {
  it('runs approve on a and A and discard on d and D', () => {
    const onApprove = vi.fn();
    const onDelete = vi.fn();
    mount({ onApprove, onDelete });
    const event = press('a');
    press('A');
    press('d');
    press('D');
    expect(onApprove).toHaveBeenCalledTimes(2);
    expect(onDelete).toHaveBeenCalledTimes(2);
    expect(event.defaultPrevented).toBe(true);
  });

  it('keeps the existing t and / shortcuts', () => {
    const onToggleTheme = vi.fn();
    const onFocusSearch = vi.fn();
    mount({ onToggleTheme, onFocusSearch });
    press('t');
    press('/');
    expect(onToggleTheme).toHaveBeenCalledTimes(1);
    expect(onFocusSearch).toHaveBeenCalledTimes(1);
  });

  it('does nothing for a key without a callback and does not prevent default', () => {
    mount({ onDelete: vi.fn() });
    expect(press('a').defaultPrevented).toBe(false);
  });

  it('ignores single-key shortcuts while typing in a form field or editable area', () => {
    const onApprove = vi.fn();
    mount({ onApprove });
    for (const tag of ['input', 'textarea', 'select']) {
      const el = document.createElement(tag);
      document.body.appendChild(el);
      el.focus();
      press('a', {}, el);
    }
    const editable = document.createElement('div');
    editable.contentEditable = 'true';
    // jsdom has no isContentEditable: define it like a browser would
    Object.defineProperty(editable, 'isContentEditable', { value: true });
    editable.tabIndex = 0;
    document.body.appendChild(editable);
    editable.focus();
    press('a', {}, editable);
    expect(onApprove).not.toHaveBeenCalled();
  });

  it('ignores them while a modal dialog is open', () => {
    const onApprove = vi.fn();
    const onToggleTheme = vi.fn();
    mount({ onApprove, onToggleTheme });
    const dialog = document.createElement('div');
    dialog.setAttribute('role', 'dialog');
    dialog.setAttribute('aria-modal', 'true');
    document.body.appendChild(dialog);
    press('a');
    press('t');
    expect(onApprove).not.toHaveBeenCalled();
    expect(onToggleTheme).not.toHaveBeenCalled();
    dialog.remove();
    press('a');
    expect(onApprove).toHaveBeenCalledTimes(1);
  });

  it('ignores modifier combinations and key repeat', () => {
    const onApprove = vi.fn();
    mount({ onApprove });
    press('a', { metaKey: true });
    press('a', { ctrlKey: true });
    press('a', { altKey: true });
    press('a', { repeat: true });
    expect(onApprove).not.toHaveBeenCalled();
  });

  it('enabled=false turns single-key shortcuts off but not Escape or Cmd+Enter', () => {
    const onApprove = vi.fn();
    const onDelete = vi.fn();
    const onToggleTheme = vi.fn();
    const onEscape = vi.fn();
    const onGenerate = vi.fn();
    mount({ onApprove, onDelete, onToggleTheme, onEscape, onGenerate, enabled: false });
    press('a');
    press('d');
    press('t');
    press('Escape');
    press('Enter', { metaKey: true });
    expect(onApprove).not.toHaveBeenCalled();
    expect(onDelete).not.toHaveBeenCalled();
    expect(onToggleTheme).not.toHaveBeenCalled();
    expect(onEscape).toHaveBeenCalledTimes(1);
    expect(onGenerate).toHaveBeenCalledTimes(1);
  });

  it('removes its listener on unmount', () => {
    const onApprove = vi.fn();
    mount({ onApprove });
    act(() => root.unmount());
    press('a');
    expect(onApprove).not.toHaveBeenCalled();
    root = createRoot(container);
  });
});
