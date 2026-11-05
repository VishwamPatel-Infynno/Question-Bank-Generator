#!/usr/bin/env node
/**
 * Lists CSS class selectors in src/styles that nothing in src (or index.html) mentions.
 *
 *   node scripts/check-unused-css.mjs          report; exit 1 when unused classes exist
 *   node scripts/check-unused-css.mjs --list   print only the class names
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

if (process.argv.includes('--list')) {
  console.log(unused.join('\n'));
} else if (unused.length) {
  console.error(`${unused.length} CSS class(es) are not used anywhere in src:\n  ${unused.join('\n  ')}`);
} else {
  console.log('No unused CSS classes.');
}
process.exit(unused.length && !process.argv.includes('--list') ? 1 : 0);
