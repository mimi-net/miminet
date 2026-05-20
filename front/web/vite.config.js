import { defineConfig } from 'vite';
import { readFileSync, mkdirSync, writeFileSync, existsSync } from 'fs';
import { dirname, resolve } from 'path';

const STATIC_ROOT = resolve(__dirname, '../src/static');
const DIST_ROOT = resolve(STATIC_ROOT, 'dist');

const CLASSIC_BUNDLE = [
  'netfront/state.js',
  'netfront/show_config.js',
  'netfront/network_ops.js',
  'netfront/draw.js',
  'netfront/simulation.js',
  'netfront/update_config.js',
  'netfront/runtime.js',
  'config_forms/common.js',
  'config_forms/device.js',
  'config_forms/shared.js',
  'config_forms/helpers.js',
  'config_forms/jobs.js',
  'config_forms/edit_jobs.js',
];

const concatClassicScripts = () => ({
  name: 'miminet-concat-classic-scripts',
  apply: 'build',
  closeBundle() {
    const parts = [];
    for (const rel of CLASSIC_BUNDLE) {
      const abs = resolve(STATIC_ROOT, rel);
      if (!existsSync(abs)) {
        throw new Error(`Bundle source missing: ${abs}`);
      }
      parts.push(readFileSync(abs, 'utf8'));
    }
    const outFile = resolve(DIST_ROOT, 'miminet.classic.js');
    mkdirSync(dirname(outFile), { recursive: true });
    writeFileSync(outFile, parts.join('\n'));
  },
});

export default defineConfig({
  build: {
    outDir: DIST_ROOT,
    emptyOutDir: true,
    rollupOptions: {
      input: resolve(__dirname, 'src/main.js'),
      output: {
        entryFileNames: 'miminet.entry.js',
        format: 'iife',
        name: 'MiminetEntry',
      },
    },
  },
  plugins: [concatClassicScripts()],
});
