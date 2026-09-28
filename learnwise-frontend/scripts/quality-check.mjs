import fs from 'node:fs';
import path from 'node:path';

const root = process.cwd();
const cssFiles = [];
function collect(directory) {
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const file = path.join(directory, entry.name);
    if (entry.isDirectory()) collect(file);
    else if (entry.name.endsWith('.css')) cssFiles.push(file);
  }
}

collect(path.join(root, 'src'));
const longLines = cssFiles.flatMap(file => fs.readFileSync(file, 'utf8').split('\n').map((line, index) => ({ file, line: index + 1, length: line.length })).filter(item => item.length > 1800));
const requiredSignals = [
  ['homepage tab semantics', 'src/features/public/components/SignatureSections.jsx', /role="tab"[\s\S]*aria-controls/],
  ['learning example announcements', 'src/features/public/components/LearningDemo.jsx', /aria-live="polite"/],
  ['educator illustrative labeling', 'src/features/public/pages/EducatorLandingPage.jsx', /Illustrative view/],
  ['public educator route', 'src/routes/routeManifest.js', /\/educators/],
  ['valid feature panel element', 'src/features/public/components/SignatureSections.jsx', /<div id=\{`feature-panel-\$\{active\.id\}`\} role="tabpanel"/],
  ['optimized wordmark asset', 'src/features/public/components/BrandMark.jsx', /learnwise-wordmark\.webp/],
  ['enforced deployment CSP', 'public/_headers', /Content-Security-Policy:.*require-trusted-types-for 'script'/],
  ['linked LLM site guide', 'public/llms.txt', /\[Home\]\(https:\/\/learnwise\.ai\/\)/],
];
const missing = requiredSignals.filter(([, file, pattern]) => !pattern.test(fs.readFileSync(path.join(root, file), 'utf8')));
if (longLines.length || missing.length) {
  console.error('Quality check failed.');
  if (longLines.length) console.error(longLines);
  if (missing.length) console.error(missing.map(([name]) => name));
  process.exit(1);
}
console.log(`Quality check passed: ${cssFiles.length} stylesheets and ${requiredSignals.length} product signals verified.`);
