(function() {
  try {
    const migrated = localStorage.getItem('mcat_theme_migrated_light_v1');
    const saved = localStorage.getItem('mcat_theme');
    if (!migrated) {
      localStorage.setItem('mcat_theme_migrated_light_v1', 'true');
      localStorage.setItem('mcat_theme', 'light');
      document.documentElement.setAttribute('data-theme', 'light');
    } else if (saved === 'dark') {
      document.documentElement.setAttribute('data-theme', 'dark');
    } else {
      document.documentElement.setAttribute('data-theme', 'light');
    }
  } catch {
    document.documentElement.setAttribute('data-theme', 'light');
  }
})();

// Fonts: the stylesheet is declared media="print" (non-blocking). Switching it on after parsing
// keeps first paint independent of Google Fonts without an inline onload handler (CSP-friendly).
document.addEventListener('DOMContentLoaded', function () {
  const fonts = document.getElementById('app-fonts');
  if (fonts) fonts.media = 'all';
});
