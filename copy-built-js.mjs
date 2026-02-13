import { mkdirSync, copyFileSync, readFileSync, writeFileSync } from "fs";
import { dirname } from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

function ensureDir(dir) {
  mkdirSync(dir, { recursive: true });
}

function copy(src, dest) {
  ensureDir(dirname(dest));
  copyFileSync(src, dest);
  console.log(`Copied ${src} -> ${dest}`);
}

function removePlotlyImport(filePath) {
  try {
    let content = readFileSync(filePath, 'utf8');
    // Remove the Plotly import line
    content = content.replace(/import \* as Plotly from "plotly\.js";\n/g, '');
    writeFileSync(filePath, content);
    console.log(`Removed Plotly import from ${filePath}`);
  } catch (err) {
    console.error(`Error processing ${filePath}:`, err);
  }
}

try {
  const foamflaskSrc = `${__dirname}/static/js-build/static/ts/foamflask_frontend.js`;
  const foamflaskDest = `${__dirname}/static/js/foamflask_frontend.js`;

  const isoSrc = `${__dirname}/static/js-build/static/ts/frontend/isosurface.js`;
  const isoDest = `${__dirname}/static/js/frontend/isosurface.js`;

  copy(foamflaskSrc, foamflaskDest);
  copy(isoSrc, isoDest);

  // Remove Plotly import from the main frontend file
  removePlotlyImport(foamflaskDest);
} catch (err) {
  console.error("Error copying built JS files:", err);
  process.exit(1);
}
