import { defineConfig } from 'vitest/config';
import { resolve } from 'path';

export default defineConfig({
  test: {
    environment: 'jsdom', // Use jsdom for browser-like environment
    globals: true, // Makes expect and other test globals available without imports
    include: ['src/**/*.test.ts'],
    exclude: ['src/api/**/*.test.ts'], // Exclude tests from symlinked files
    alias: {
      '@': resolve(__dirname, 'src'),
    },
    deps: {
      optimizer: {
        web: {
          include: ['openapi-fetch']
        }
      }
    },
  },
});