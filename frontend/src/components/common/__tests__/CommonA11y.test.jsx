// @vitest-environment jsdom
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import Modal from '../Modal';
import ErrorBoundary from '../ErrorBoundary';
import { ToastContainer } from '../Toast';

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
const render = (el) => act(() => root.render(el));
const mouse = (el, type) => act(() => { el.dispatchEvent(new MouseEvent(type, { bubbles: true })); });

describe('Modal', () => {
  it('only closes when press and click both land on the backdrop', () => {
    const onClose = vi.fn();
    render(<Modal isOpen onClose={onClose} title="T"><button>x</button></Modal>);
    const backdrop = container.querySelector('[role="dialog"]');
    const card = container.querySelector('.modal-card-base');

    mouse(card, 'mousedown');
    mouse(backdrop, 'click'); // drag ended on the backdrop
    expect(onClose).not.toHaveBeenCalled();

    mouse(backdrop, 'mousedown');
    mouse(backdrop, 'click');
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('always has an accessible name', () => {
    render(<Modal isOpen onClose={() => {}} title="Hello"><p>b</p></Modal>);
    const d = container.querySelector('[role="dialog"]');
    expect(d.getAttribute('aria-labelledby')).toBeTruthy();
    expect(d.hasAttribute('aria-label')).toBe(false);

    render(<Modal isOpen onClose={() => {}}><p>b</p></Modal>);
    expect(container.querySelector('[role="dialog"]').getAttribute('aria-label')).toBe('Dialog');

    render(<Modal isOpen onClose={() => {}} ariaLabel="Custom"><p>b</p></Modal>);
    expect(container.querySelector('[role="dialog"]').getAttribute('aria-label')).toBe('Custom');
  });

  it('skips hidden controls when wrapping Tab focus', () => {
    render(
      <Modal isOpen onClose={() => {}} title="T">
        <button id="a">a</button>
        <button id="b">b</button>
        <button id="hid" style={{ display: 'none' }}>h</button>
      </Modal>
    );
    // The header close button is first; focus the last visible control and Tab forward
    const last = container.querySelector('#b');
    last.focus();
    const ev = new KeyboardEvent('keydown', { key: 'Tab', bubbles: true, cancelable: true });
    act(() => { window.dispatchEvent(ev); });
    // Wrapped to first focusable (close button), not trapped on the hidden button
    expect(ev.defaultPrevented).toBe(true);
    expect(document.activeElement.getAttribute('aria-label')).toBe('Close modal');
    expect(document.activeElement.id).not.toBe('hid');
  });
});

describe('ToastContainer', () => {
  it('keeps a polite live region mounted when empty and uses alert for errors', () => {
    render(<ToastContainer toasts={[]} onDismiss={() => {}} />);
    const region = container.querySelector('[aria-live="polite"]');
    expect(region).not.toBeNull();

    render(
      <ToastContainer
        toasts={[{ id: 1, type: 'error', message: 'bad' }, { id: 2, type: 'info', message: 'ok' }]}
        onDismiss={() => {}}
      />
    );
    expect(container.querySelectorAll('[role="alert"]').length).toBe(1);
    expect(container.querySelector('[role="alert"]').textContent).toContain('bad');
  });
});

describe('ErrorBoundary (root usage)', () => {
  it('shows fallback, logs to console, and calls onReset on retry', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});
    const onReset = vi.fn();
    function Bomb() { throw new Error('kaboom'); }
    render(<ErrorBoundary fallbackLabel="the application" onReset={onReset}><Bomb /></ErrorBoundary>);
    expect(container.textContent).toContain('Unable to load the application');
    expect(container.textContent).toContain('kaboom');
    expect(spy).toHaveBeenCalled();
    act(() => { container.querySelector('.btn-primary').click(); });
    expect(onReset).toHaveBeenCalled();
    spy.mockRestore();
  });
});
