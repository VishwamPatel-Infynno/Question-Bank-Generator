import { useState, useEffect } from 'react';

export function useTheme() {
  const [theme, setTheme] = useState(() => {
    try {
      const saved = localStorage.getItem('mcat_theme');
      if (saved === 'light' || saved === 'dark') return saved;
      // Default to Alabaster Light theme for optimal readability
      return 'light';
    } catch {
      return 'light';
    }
  });

  useEffect(() => {
    try {
      document.documentElement.setAttribute('data-theme', theme);
      localStorage.setItem('mcat_theme', theme);
    } catch {
      // Ignore localStorage write failures in restricted environments
    }
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  return { theme, toggleTheme };
}
