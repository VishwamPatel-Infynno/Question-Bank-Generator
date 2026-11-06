#!/usr/bin/env node
/**
 * Lists CSS class selectors in src/styles that nothing in src (or index.html) mentions.
 *
 *   node scripts/check-unused-css.mjs          report; exit 1 when unused or missing classes exist
 *   node scripts/check-unused-css.mjs --list   print only the unused class names
 *
 * It also reports the reverse: class names written literally in JSX (`className="a b"` or the
 * static parts of a className template literal) that no stylesheet defines, which is how a
 * typo'd or never-written rule shows up.
 *
 * A class counts as used when its name appears anywhere in the JS/JSX sources, or when a
 * template literal builds it from a known dynamic prefix (see DYNAMIC_PREFIXES). Classes toggled
 * only from CSS (e.g. state classes added by other stylesheets) belong in ALLOWED.
 */
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const src = join(root, 'src');

// Class names are assembled at runtime from these prefixes (e.g. `tier-${id}`, `status-${x}`)
const DYNAMIC_PREFIXES = ['tier-', 'status-', 'badge-', 'wizard-tier-', 'section-'];
const ALLOWED = new Set([]);
// Classes JSX may use without a stylesheet rule (state hooks other CSS reads, or scoped names)
const ALLOWED_MISSING = new Set(['active', 'open', 'selected', 'expanded', 'current', 'completed', 'running', 'disabled', 'copied', 'placeholder']);

function walk(dir, out = []) {
  for (const name of readdirSync(dir)) {
    const full = join(dir, name);
    if (statSync(full).isDirectory()) {
      if (name === '__tests__' || name === 'node_modules') continue;
      walk(full, out);
    } else out.push(full);
  }
  return out;
}

const files = walk(src);
const sourceText = files
  .filter((f) => /\.(jsx?|html)$/.test(f))
  .map((f) => readFileSync(f, 'utf8'))
  .join('\n') + readFileSync(join(root, 'index.html'), 'utf8');

const classes = new Set();
for (const css of files.filter((f) => f.endsWith('.css') && f.includes('styles'))) {
  const text = readFileSync(css, 'utf8').replace(/\/\*[\s\S]*?\*\//g, '');
  for (const m of text.matchAll(/\.(-?[_a-zA-Z][\w-]*)/g)) classes.add(m[1]);
}

const unused = [...classes]
  .filter((c) => !ALLOWED.has(c))
  .filter((c) => !DYNAMIC_PREFIXES.some((p) => c.startsWith(p)))
  .filter((c) => !new RegExp(`(^|[^\\w-])${c.replace(/[-/\\^$*+?.()|[\]{}]/g, '\\$&')}($|[^\\w-])`).test(sourceText))
  .sort();

// Reverse check: literal class names in JSX that no stylesheet defines
const referenced = new Set();
for (const f of files.filter((f) => /\.jsx?$/.test(f))) {
  const src = readFileSync(f, 'utf8');
  for (const m of src.matchAll(/className=(?:"([^"]*)"|'([^']*)'|\{`([^`]*)`\})/g)) {
    const text = (m[1] ?? m[2] ?? m[3] ?? '').replace(/\$\{[^}]*\}/g, ' ');
    for (const token of text.split(/\s+/)) {
      if (/^-?[_a-zA-Z][\w-]*$/.test(token)) referenced.add(token);
    }
  }
}
const missing = [...referenced]
  .filter((c) => !classes.has(c) && !ALLOWED_MISSING.has(c))
  .filter((c) => !DYNAMIC_PREFIXES.some((p) => c.startsWith(p)))
  .sort();

if (process.argv.includes('--list')) {
  console.log(unused.join('\n'));
} else {
  if (unused.length) {
    console.error(`${unused.length} CSS class(es) are not used anywhere in src:\n  ${unused.join('\n  ')}`);
  }
  if (missing.length) {
    console.error(`${missing.length} class name(s) used in JSX have no CSS rule:\n  ${missing.join('\n  ')}`);
  }
  if (!unused.length && !missing.length) console.log('No unused or missing CSS classes.');
}
process.exit((unused.length || missing.length) && !process.argv.includes('--list') ? 1 : 0);
