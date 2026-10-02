/// <reference types="vitest" />
import vue from "@vitejs/plugin-vue";
import path from "path";
import { fileURLToPath } from "url";
import { defineConfig, type Plugin } from "vite";

import { i18nPlugin } from "./tests/vitest/test-plugin";
import { yamlPlugin } from "./tests/vitest/yaml-plugin";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/**
 * Plugin to redirect portal-vue imports to our mock.
 * portal-vue uses Vue.extend which doesn't exist in Vue 3.
 */
function portalVueMockPlugin(): Plugin {
    const mockPath = path.resolve(__dirname, "./tests/vitest/__mocks__/portal-vue.js");
    return {
        name: "portal-vue-mock",
        enforce: "pre",
        resolveId(source, importer) {
            // Intercept any import of portal-vue
            if (source === "portal-vue" || source.includes("node_modules/portal-vue")) {
                return mockPath;
            }
            return null;
        },
        // Also handle load for files that slip through
        load(id) {
            if (id.includes("node_modules/portal-vue")) {
                return `export * from "${mockPath}"; export { default } from "${mockPath}";`;
            }
            return null;
        },
    };
}

// List of modules that need to be transformed
const modulesToTransform = [
    "axios",
    "bootstrap-vue",
    "portal-vue",
    "rxjs",
    "@hirez_io",
    "pretty-bytes",
    "@fortawesome",
    "ro-crate-zip-explorer",
    "yaml",
    // Vitest treats node_modules packages as SSR-external by default, which
    // resolves their own `import ... from "vue"` via plain Node resolution
    // instead of the `vue: "@vue/compat"` alias below. That gives these
    // packages a second, separate Vue module instance -- so a ref they create
    // (test-utils' app/renderer, a Pinia store's state, vue-router's route)
    // tracks dependents through a different reactivity graph than the one
    // components render with, and mutating it never triggers a re-render even
    // though reads see the new value. Inlining them routes their "vue" import
    // through the same alias as everything else.
    "@vue/test-utils",
    "vue-router",
    "pinia",
    "@pinia/testing",
    // @vueuse reaches Vue through vue-demi's `export * from "vue"`.
    "vue-demi",
    "@vueuse",
    // The `vue` alias below points at compat's ESM build; inline it too so it's
    // one transformed module (with plugin-vue's feature-flag defines) rather
    // than a second copy Node loads on its own.
    "@vue/compat",
];

export default defineConfig({
    plugins: [
        portalVueMockPlugin(), // Must be first to intercept portal-vue imports
        vue({
            template: {
                compilerOptions: {
                    // Match the app build, see vite.config.mjs.
                    comments: false,
                    compatConfig: {
                        MODE: 2,
                    },
                },
            },
        }),
        i18nPlugin(),
        yamlPlugin(),
    ],
    test: {
        globals: false,
        environment: "happy-dom",
        setupFiles: ["./tests/vitest/setup.ts"],
        environmentOptions: {
            happyDOM: {
                url: "http://localhost/",
            },
        },
        coverage: {
            provider: "v8",
            reporter: ["text", "json", "html"],
            exclude: [
                "node_modules/",
                "tests/",
                "dist/",
                "**/*.d.ts",
                "**/*.test.{js,ts}",
                "**/mock*.{js,ts}",
                "**/__mocks__/",
            ],
        },
        // Transform modules that need it
        server: {
            deps: {
                inline: modulesToTransform,
            },
        },
        // Force these modules through Vite's transform pipeline
        deps: {
            optimizer: {
                web: {
                    // Exclude portal-vue from pre-bundling so our plugin can intercept it
                    exclude: ["portal-vue"],
                },
            },
        },
        // Use thread pool for faster test execution
        pool: "threads",
        // Test file patterns
        include: ["src/**/*.test.{js,ts}", "tests/vitest/**/*.test.{js,ts}", "packages/*/src/**/*.test.{js,ts}"],
        // Exclude patterns
        exclude: ["node_modules", "dist", "**/dist/**"],
    },
    resolve: {
        alias: {
            // galaxy-ui resolves through the workspace symlink and its exports
            // map, so it needs no alias entry here.
            // Vue Test Utils adapter - wraps mount/shallowMount to handle old v1 patterns
            "@vue/test-utils": path.resolve(__dirname, "./tests/vitest/__mocks__/vue-test-utils-adapter.ts"),
            // Vue Router adapter - provides both VR3 (default export, constructor) and VR4 APIs
            "vue-router": path.resolve(__dirname, "./tests/vitest/__mocks__/vue-router-adapter.ts"),
            // Use @vue/compat for Vue 3 compatibility mode. Point at its ESM build:
            // the package's Node entry is CJS, which re-export-all modules like
            // vue-demi can't see through. The full build, since some tests
            // compile templates at runtime.
            vue: path.resolve(__dirname, "node_modules/@vue/compat/dist/vue.esm-bundler.js"),
            // Use ESM version of bootstrap-vue so Vite can transform its imports
            "bootstrap-vue": path.resolve(__dirname, "node_modules/bootstrap-vue/esm/index.js"),
            // Mock portal-vue for Vue 3 compatibility (used by bootstrap-vue)
            "portal-vue": path.resolve(__dirname, "./tests/vitest/__mocks__/portal-vue.js"),
            // Match former Jest's module name mapping
            "@": path.resolve(__dirname, "./src"),
            "@tests": path.resolve(__dirname, "./tests"),
            config: path.resolve(__dirname, "./tests/vitest/__mocks__/config.js"),
            config$: path.resolve(__dirname, "./tests/vitest/__mocks__/config.js"),
            "utils/localization$": path.resolve(__dirname, "./tests/vitest/__mocks__/localization.js"),
            "viz/trackster$": path.resolve(__dirname, "./tests/vitest/__mocks__/trackster.js"),
            // Handle i18n imports
            "^i18n!(.*)": path.resolve(__dirname, "./tests/vitest/__mocks__/localization.js"),
            // Handle handsontable
            handsontable: "handsontable/dist/handsontable.js",
            // Handle rxjs scheduler
            "rxjs/internal/scheduler/AsyncScheduler": "rxjs/dist/esm/internal/scheduler/AsyncScheduler.js",
        },
        // Ensure .vue files are resolved
        extensions: [".js", ".ts", ".json", ".vue", ".yml", ".txt"],
    },
    // CSS handling
    css: {
        modules: {
            // Mock CSS modules like Jest does
            generateScopedName: "[local]",
        },
    },
    // Build optimizations for test mode
    optimizeDeps: {
        include: ["vue", "@vue/test-utils", ...modulesToTransform],
    },
});
