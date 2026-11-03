import React, { useState, useRef, useEffect, useId } from 'react';
import { ChevronDown, Check, Search } from 'lucide-react';

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
const EMPTY_ARRAY = [];
const EMPTY_OBJECT = Object.freeze({});

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
  align = 'left'
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
        setHighlightedIndex(prev => {
          const current = prev >= 0 ? prev : activeIndex;
          return current < filteredOptions.length - 1 ? current + 1 : 0;
        });
        break;
      case 'ArrowUp':
        e.preventDefault();
        setHighlightedIndex(prev => {
          const current = prev >= 0 ? prev : activeIndex;
          return current > 0 ? current - 1 : filteredOptions.length - 1;
        });
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
      className="custom-select-container"
      style={{
        position: 'relative',
        display: 'inline-block',
        width: '100%',
        ...style
      }}
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
        className={`custom-select-trigger ${isOpen ? 'active' : ''}`}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '8px',
          padding: isSmall ? '5px 10px' : '8px 12px',
          background: 'var(--bg-surface-elevated)',
          border: `1px solid ${isOpen ? 'var(--brand-primary)' : 'var(--border-medium)'}`,
          borderRadius: 'var(--radius-sm)',
          color: selectedOption ? 'var(--text-primary)' : 'var(--text-muted)',
          fontSize: isSmall ? '0.75rem' : '0.825rem',
          fontWeight: 500,
          cursor: disabled ? 'not-allowed' : 'pointer',
          opacity: disabled ? 0.6 : 1,
          transition: 'all var(--transition-fast)',
          boxShadow: isOpen ? '0 0 0 2px var(--brand-glow)' : 'var(--shadow-xs)',
          textAlign: 'left'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0, flex: 1 }}>
          {(icon || selectedOption?.icon) && (
            <span style={{ display: 'flex', color: 'var(--brand-primary)', flexShrink: 0 }}>
              {selectedOption?.icon || icon}
            </span>
          )}

          <span
            style={{
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              flex: 1
            }}
          >
            {selectedOption ? selectedOption.label : placeholder}
          </span>

          {(badge || selectedOption?.badge) && (
            <span
              className="badge-minimal"
              style={{
                fontSize: '0.625rem',
                padding: '1px 6px',
                flexShrink: 0
              }}
            >
              {selectedOption?.badge || badge}
            </span>
          )}
        </div>

        <ChevronDown
          size={isSmall ? 13 : 15}
          style={{
            flexShrink: 0,
            color: 'var(--text-muted)',
            transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)',
            transition: 'transform var(--transition-fast)'
          }}
        />
      </button>

      {/* Popover Floating Listbox */}
      {isOpen && (
        <div
          id={listboxId}
          ref={listboxRef}
          role="listbox"
          tabIndex={-1}
          style={{
            position: 'absolute',
            top: 'calc(100% + 4px)',
            [align === 'right' ? 'right' : 'left']: 0,
            width: '100%',
            minWidth: isSmall ? '180px' : '220px',
            maxWidth: '420px',
            maxHeight: '320px',
            background: 'var(--bg-surface-elevated)',
            border: '1px solid var(--border-medium)',
            borderRadius: 'var(--radius-sm)',
            boxShadow: 'var(--shadow-lg)',
            zIndex: 100,
            backdropFilter: 'blur(16px)',
            WebkitBackdropFilter: 'blur(16px)',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            animation: 'fadeIn 0.15s ease-out',
            ...menuStyle
          }}
        >
          {/* Optional Search Filter Header */}
          {isSearchable && (
            <div
              style={{
                padding: '8px',
                borderBottom: '1px solid var(--border-light)',
                background: 'var(--bg-surface-subtle)',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
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
                style={{
                  width: '100%',
                  background: 'transparent',
                  border: 'none',
                  fontSize: '0.75rem',
                  color: 'var(--text-primary)',
                  outline: 'none'
                }}
              />
            </div>
          )}

          {/* Options Scroll Container */}
          <div
            style={{
              overflowY: 'auto',
              maxHeight: '260px',
              padding: '4px'
            }}
          >
            {filteredOptions.length === 0 ? (
              <div
                style={{
                  padding: '12px 14px',
                  fontSize: '0.75rem',
                  color: 'var(--text-muted)',
                  textAlign: 'center'
                }}
              >
                No matching options
              </div>
            ) : (
              filteredOptions.map((opt, idx) => {
                const isSelected = String(opt.value) === String(value);
                const isHighlighted = idx === activeIndex;

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
                    style={{
                      padding: isSmall ? '6px 10px' : '8px 12px',
                      borderRadius: 'var(--radius-xs)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      gap: '8px',
                      cursor: opt.disabled ? 'not-allowed' : 'pointer',
                      opacity: opt.disabled ? 0.5 : 1,
                      background: isSelected
                        ? 'var(--brand-light)'
                        : isHighlighted
                        ? 'var(--bg-surface-hover)'
                        : 'transparent',
                      color: isSelected ? 'var(--brand-primary)' : 'var(--text-primary)',
                      transition: 'background var(--transition-fast)'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', minWidth: 0, flex: 1 }}>
                      {opt.icon && (
                        <span
                          style={{
                            display: 'flex',
                            color: isSelected ? 'var(--brand-primary)' : 'var(--text-muted)',
                            marginTop: opt.description ? '2px' : 0,
                            flexShrink: 0
                          }}
                        >
                          {opt.icon}
                        </span>
                      )}

                      <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', minWidth: 0, flex: 1 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                          <span
                            style={{
                              fontSize: isSmall ? '0.75rem' : '0.8rem',
                              fontWeight: isSelected ? 600 : 500,
                              lineHeight: '1.3'
                            }}
                          >
                            {opt.label}
                          </span>
                          {opt.badge && (
                            <span
                              className="badge-minimal"
                              style={{
                                fontSize: '0.625rem',
                                padding: '0 5px'
                              }}
                            >
                              {opt.badge}
                            </span>
                          )}
                        </div>

                        {opt.description && (
                          <span
                            style={{
                              fontSize: '0.675rem',
                              color: 'var(--text-muted)',
                              lineHeight: '1.3'
                            }}
                          >
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
                        style={{ flexShrink: 0 }}
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
