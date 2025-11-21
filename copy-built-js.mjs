import { mkdirSync, copyFileSync } from "fs";
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

try {
  const foamflaskSrc = `${__dirname}/static/js-build/foamflask_frontend.js`;
  const foamflaskDest = `${__dirname}/static/js/foamflask_frontend.js`;

  const isoSrc = `${__dirname}/static/js-build/frontend/isosurface.js`;
  const isoDest = `${__dirname}/static/js/frontend/isosurface.js`;

  copy(foamflaskSrc, foamflaskDest);
  copy(isoSrc, isoDest);
} catch (err) {
  console.error("Error copying built JS files:", err);
  process.exit(1);
}
