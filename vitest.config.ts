import { defineConfig } from 'vitest/config';
import path from 'path';

export default defineConfig({
  test: {
    environment: 'jsdom',
    include: ['static/tests/unit/**/*.test.ts'],
    globals: true,
    alias: {
      'plotly.js': path.resolve(__dirname, './static/tests/mocks/plotly.js'),
    },
  },
});
