import { defineConfig } from 'tsup';

export default defineConfig({
  entry: ['src/index.ts'],
  format: ['esm', 'cjs'],
  dts: true,
  sourcemap: true,
  clean: true,
  treeshake: true,
  minify: false,
  target: 'es2020',
  esbuildOptions(options) {
    options.external = [
      ...options.external || [],
      // External dependencies that should not be bundled
      'openapi-fetch'
    ];
  },
});