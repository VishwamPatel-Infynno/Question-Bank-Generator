import React, { useState, useRef, useEffect, useId } from 'react';
import { ChevronDown, Check, Search } from 'lucide-react';
import { EMPTY_ARRAY, EMPTY_OBJECT } from '../../constants';
import { nextEnabledIndex } from '../../utils/selectHelpers';

/**
 * CustomSelect:
 * Universal, accessible, glassmorphism-styled dropdown component.
 *
 * Props:
 * - id: string
 * - value: any
 * - onChange: (value: any) => void
 * - options: Array<{ value: any, label: string, description?: string, icon?: React.ReactNode, badge?: string, disabled?: boolean }>
 * - placeholder?: string
 * - label?: string
 * - icon?: React.ReactNode (leading icon on trigger)
 * - badge?: string (badge on trigger)
 * - disabled?: boolean
 * - searchable?: boolean (defaults to true if options.length > 5)
 * - size?: 'sm' | 'md'
 * - style?: React.CSSProperties
 * - menuStyle?: React.CSSProperties
 * - align?: 'left' | 'right'
 */

export default function CustomSelect({
  id,
  value,
  onChange,
  options = EMPTY_ARRAY,
  placeholder = 'Select option...',
  label,
  icon,
  badge,
  disabled = false,
  searchable = undefined,
  size = 'md',
  style = EMPTY_OBJECT,
  menuStyle = EMPTY_OBJECT,
  align = 'left',
  className = ''
}) {
  const generatedId = useId();
  const selectId = id || generatedId;
  const listboxId = `${selectId}-listbox`;
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [highlightedIndex, setHighlightedIndex] = useState(-1);

  const containerRef = useRef(null);
  const triggerRef = useRef(null);
  const searchInputRef = useRef(null);
  const listboxRef = useRef(null);

  // Find currently selected option
  const selectedOption = options.find(opt => String(opt.value) === String(value));

  // Determine if search should be enabled
  const isSearchable = searchable !== undefined ? searchable : options.length > 5;

  // Filter options based on search query
  const filteredOptions = options.filter(opt => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    const matchLabel = opt.label?.toLowerCase().includes(q);
    const matchDesc = opt.description?.toLowerCase().includes(q);
    const matchBadge = opt.badge?.toLowerCase().includes(q);
    return matchLabel || matchDesc || matchBadge;
  });

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event) {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false);
        setSearchQuery('');
        setHighlightedIndex(-1);
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  // Ensure only one dropdown is open at a time app-wide
  useEffect(() => {
    function handleOtherOpen(e) {
      if (e.detail !== selectId) {
        setIsOpen(false);
        setSearchQuery('');
        setHighlightedIndex(-1);
      }
    }
    window.addEventListener('custom-select-open', handleOtherOpen);
    return () => {
      window.removeEventListener('custom-select-open', handleOtherOpen);
    };
  }, [selectId]);

  // Focus search input when opening
  useEffect(() => {
    if (isOpen && isSearchable) {
      setTimeout(() => {
        if (searchInputRef.current) {
          searchInputRef.current.focus();
        }
      }, 50);
    }
  }, [isOpen, isSearchable]);

  // Determine active highlighted index (derived, avoiding cascading renders)
  const selectedIdx = filteredOptions.findIndex(opt => String(opt.value) === String(value));
  const activeIndex = highlightedIndex >= 0 && highlightedIndex < filteredOptions.length
    ? highlightedIndex
    : (selectedIdx >= 0 ? selectedIdx : 0);

  // Scroll highlighted item into view
  useEffect(() => {
    if (isOpen && listboxRef.current && activeIndex >= 0) {
      const items = listboxRef.current.querySelectorAll('[role="option"]');
      if (items[activeIndex]) {
        items[activeIndex].scrollIntoView({ block: 'nearest' });
      }
    }
  }, [activeIndex, isOpen]);

  const handleSelect = (opt) => {
    if (opt.disabled) return;
    onChange(opt.value);
    setIsOpen(false);
    setSearchQuery('');
    setHighlightedIndex(-1);
    if (triggerRef.current) {
      triggerRef.current.focus();
    }
  };

  const handleKeyDown = (e) => {
    if (disabled) return;

    if (!isOpen) {
      if (['ArrowDown', 'ArrowUp', 'Enter', ' '].includes(e.key)) {
        e.preventDefault();
        setIsOpen(true);
        // same announcement as a click, so any other open menu closes
        window.dispatchEvent(new CustomEvent('custom-select-open', { detail: selectId }));
      }
      return;
    }

    switch (e.key) {
      case 'Escape':
        e.preventDefault();
        setIsOpen(false);
        setSearchQuery('');
        setHighlightedIndex(-1);
        if (triggerRef.current) triggerRef.current.focus();
        break;
      case 'ArrowDown':
        e.preventDefault();
        setHighlightedIndex((prev) =>
          nextEnabledIndex(filteredOptions, prev >= 0 ? prev : activeIndex, 1)
        );
        break;
      case 'ArrowUp':
        e.preventDefault();
        setHighlightedIndex((prev) =>
          nextEnabledIndex(filteredOptions, prev >= 0 ? prev : activeIndex, -1)
        );
        break;
      case 'Enter':
        e.preventDefault();
        if (activeIndex >= 0 && filteredOptions[activeIndex]) {
          handleSelect(filteredOptions[activeIndex]);
        }
        break;
      default:
        break;
    }
  };

  const isSmall = size === 'sm';

  return (
    <div
      ref={containerRef}
      className={`custom-select-container ${className}`.trim()}
      style={style}
      onKeyDown={handleKeyDown}
    >
      {/* Trigger Button */}
      <button
        ref={triggerRef}
        id={selectId}
        type="button"
        role="combobox"
        aria-expanded={isOpen}
        aria-controls={isOpen ? listboxId : undefined}
        aria-haspopup="listbox"
        aria-label={label || placeholder}
        disabled={disabled}
        onClick={() => {
          if (!disabled) {
            const next = !isOpen;
            setIsOpen(next);
            setSearchQuery('');
            if (next) {
              window.dispatchEvent(new CustomEvent('custom-select-open', { detail: selectId }));
            }
          }
        }}
        className={`custom-select-trigger ${isOpen ? 'active' : ''} ${isSmall ? 'size-sm' : 'size-md'} ${!selectedOption ? 'placeholder' : ''}`}
      >
        <div className="custom-select-trigger-content">
          {(icon || selectedOption?.icon) && (
            <span className="custom-select-trigger-icon">
              {selectedOption?.icon || icon}
            </span>
          )}

          <span className="custom-select-trigger-label">
            {selectedOption ? selectedOption.label : placeholder}
          </span>

          {(badge || selectedOption?.badge) && (
            <span className="badge-minimal custom-select-trigger-badge">
              {selectedOption?.badge || badge}
            </span>
          )}
        </div>

        <ChevronDown
          size={isSmall ? 13 : 15}
          className={`custom-select-chevron ${isOpen ? 'open' : ''}`}
        />
      </button>

      {/* Popover Floating Listbox */}
      {isOpen && (
        <div
          id={listboxId}
          ref={listboxRef}
          role="listbox"
          tabIndex={-1}
          className={`custom-select-popover ${isSmall ? 'size-sm' : 'size-md'} ${align === 'right' ? 'align-right' : 'align-left'}`}
          style={menuStyle}
        >
          {/* Optional Search Filter Header */}
          {isSearchable && (
            <div className="custom-select-search-box">
              <Search size={13} color="var(--text-muted)" />
              <input
                ref={searchInputRef}
                id={`${selectId}-search`}
                name={`${selectId}-search`}
                type="text"
                aria-label="Filter options"
                placeholder="Search..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="custom-select-search-input"
              />
            </div>
          )}

          {/* Options Scroll Container */}
          <div className="custom-select-options-list">
            {filteredOptions.length === 0 ? (
              <div className="custom-select-empty">
                No matching options
              </div>
            ) : (
              filteredOptions.map((opt, idx) => {
                const isSelected = String(opt.value) === String(value);
                const isHighlighted = idx === activeIndex;

                let optClass = `custom-select-option ${isSmall ? 'size-sm' : 'size-md'}`;
                if (isSelected) optClass += ' selected';
                else if (isHighlighted) optClass += ' highlighted';
                if (opt.disabled) optClass += ' disabled';

                return (
                  <div
                    key={String(opt.value)}
                    role="option"
                    aria-selected={isSelected}
                    tabIndex={opt.disabled ? -1 : 0}
                    onClick={() => handleSelect(opt)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        handleSelect(opt);
                      }
                    }}
                    onMouseEnter={() => setHighlightedIndex(idx)}
                    className={optClass}
                  >
                    <div className="custom-select-option-content">
                      {opt.icon && (
                        <span className="custom-select-option-icon">
                          {opt.icon}
                        </span>
                      )}

                      <div className="custom-select-option-text">
                        <div className="custom-select-option-header">
                          <span className="custom-select-option-label">
                            {opt.label}
                          </span>
                          {opt.badge && (
                            <span className="badge-minimal custom-select-option-badge">
                              {opt.badge}
                            </span>
                          )}
                        </div>

                        {opt.description && (
                          <span className="custom-select-option-desc">
                            {opt.description}
                          </span>
                        )}
                      </div>
                    </div>

                    {isSelected && (
                      <Check
                        size={14}
                        color="var(--brand-primary)"
                        strokeWidth={2.5}
                        className="custom-select-option-check"
                      />
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}
