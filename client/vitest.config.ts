/// <reference types="vitest" />
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue2";
import path from "path";
import { fileURLToPath } from "url";
import { i18nPlugin } from "./tests/vitest/test-plugin";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// List of modules that need to be transformed
const modulesToTransform = [
    "axios",
    "bootstrap-vue",
    "rxjs",
    "@hirez_io",
    "winbox",
    "pretty-bytes",
    "@fortawesome",
    "ro-crate-zip-explorer",
    "yaml",
];

export default defineConfig({
    plugins: [vue(), i18nPlugin()],
    test: {
        globals: true,
        environment: "jsdom",
        setupFiles: ["./tests/vitest/setup.ts"],
        environmentOptions: {
            jsdom: {
                customExportConditions: ["msw"],
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
                "**/*.spec.{js,ts}",
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
        // Use thread pool for faster test execution
        pool: "threads",
        // Test file patterns
        include: ["src/**/*.vitest.{test,spec}.{js,ts}", "tests/vitest/**/*.{test,spec}.{js,ts}"],
        // Exclude patterns
        exclude: ["node_modules", "dist", "tests/jest/**"],
    },
    resolve: {
        alias: {
            // Match Jest's module name mapping
            "@": path.resolve(__dirname, "./src"),
            "@tests": path.resolve(__dirname, "./tests"),
            config$: path.resolve(__dirname, "./tests/vitest/__mocks__/config.js"),
            "utils/localization$": path.resolve(__dirname, "./tests/vitest/__mocks__/localization.js"),
            "viz/trackster$": path.resolve(__dirname, "./tests/vitest/__mocks__/trackster.js"),
            // Handle i18n imports
            "^i18n!(.*)": path.resolve(__dirname, "./tests/vitest/__mocks__/localization.js"),
            // Handle handsontable
            handsontable: "handsontable/dist/handsontable.js",
            // Handle dexie
            dexie: "dexie/dist/dexie.js",
            // Handle rxjs scheduler
            "rxjs/internal/scheduler/AsyncScheduler": "rxjs/dist/esm/internal/scheduler/AsyncScheduler.js",
        },
        // Ensure .vue files are resolved
        extensions: [".js", ".ts", ".json", ".vue", ".yml", ".txt"],
    },
    // Define global variables
    define: {
        __webpack_public_path__: '""',
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