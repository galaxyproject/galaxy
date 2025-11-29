import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import ViteYaml from "@modyfi/vite-plugin-yaml";
import inject from "@rollup/plugin-inject";
import vue from "@vitejs/plugin-vue2";
import { defineConfig } from "vite";
import tsconfigPaths from "vite-tsconfig-paths";

import { buildMetadataPlugin } from "./vite-plugin-build-metadata.js";
import { galaxyLegacyPlugin } from "./vite-plugin-galaxy-legacy.js";

const __dirname = dirname(fileURLToPath(import.meta.url));

/**
 * Plugin to fix D3 v3 ES module compatibility
 * D3 v3 is an IIFE that expects `this` to be `window` at the module level.
 * In ES modules, `this` is `undefined`. This plugin wraps the code to
 * execute with the correct global context.
 */
function d3v3CompatPlugin() {
    return {
        name: "d3v3-compat",
        transform(code, id) {
            // Only transform the d3v3 main file
            if (
                (id.includes("node_modules/d3v3/d3.js") || id.includes("node_modules\\d3v3\\d3.js")) &&
                code.startsWith("!function()")
            ) {
                // The D3 v3 code is: !function() { ... }();
                // We need to change it to: !function() { ... }.call(window);
                // This ensures `this` inside the IIFE refers to `window`
                const transformed = code.replace(
                    /\}(\s*)\(\s*\)\s*;?\s*$/,
                    "}.call(typeof window !== 'undefined' ? window : globalThis);",
                );
                return {
                    code: transformed,
                    map: null,
                };
            }
            return null;
        },
    };
}

export default defineConfig({
    // Use relative base so CSS asset references work with any proxy prefix.
    // The HTML script tags use url_for() which handles the prefix correctly.
    base: "./",
    define: {
        // Make jQuery available globally for plugins and legacy code
        global: "globalThis",
        // Define build system for runtime checks
        __GALAXY_BUILD_SYSTEM__: JSON.stringify("vite"),
        // Define build timestamp
        __buildTimestamp__: JSON.stringify(new Date().toISOString()),
    },
    plugins: [
        vue(), // Vue 2.7 support
        tsconfigPaths(), // TypeScript path resolution
        ViteYaml(), // YAML file support
        galaxyLegacyPlugin(), // Handle legacy module resolution
        buildMetadataPlugin(), // Generate build metadata (replaces DumpMetaPlugin)
        d3v3CompatPlugin(), // Fix D3 v3 ES module compatibility
        // Inject imports for underscore and Buffer
        // jQuery is set up as window.$ and window.jQuery by libs.bundled.js
        // Note: We don't inject jQuery here to avoid circular dependencies with code splitting
        inject({
            include: ["**/*.js", "**/*.ts", "**/*.vue"],
            exclude: ["**/node_modules/**"],
            _: "underscore",
            Buffer: ["buffer", "Buffer"],
        }),
    ],
    // resolve aliases are handled by galaxyLegacyPlugin
    css: {
        preprocessorOptions: {
            scss: {
                quietDeps: true,
                silenceDeprecations: ["import", "color-functions", "global-builtin"],
                includePaths: ["src/style", "src/style/scss", "node_modules"],
            },
        },
    },
    build: {
        outDir: "dist",
        emptyOutDir: true,
        // Generate manifest.json for production
        manifest: true,
        // Disable CSS code splitting - combine all CSS into one file
        cssCodeSplit: false,
        // Generate sourcemaps when GXY_BUILD_SOURCEMAPS is set
        sourcemap: !!process.env.GXY_BUILD_SOURCEMAPS,
        rollupOptions: {
            input: {
                // Entry points that will be referenced in templates
                // libs must be loaded first - it exposes globals (jQuery, bundleEntries, config)
                libs: resolve(__dirname, "src/entry/libs.js"),
                analysis: resolve(__dirname, "src/entry/analysis/index.ts"),
                generic: resolve(__dirname, "src/entry/generic.js"),
            },
            output: {
                entryFileNames: "[name].bundled.js",
                chunkFileNames: "[name]-[hash].js",
                // CSS should be named 'base.css' to match what templates expect
                assetFileNames: (assetInfo) => {
                    if (assetInfo.name && assetInfo.name.endsWith(".css")) {
                        return "base.css";
                    }
                    return "[name]-[hash].[ext]";
                },
                manualChunks: (id) => {
                    // Put jQuery in its own chunk - jquery-migrate is imported dynamically
                    if (id.includes("node_modules/jquery/") && !id.includes("jquery-migrate")) {
                        return "jquery-core";
                    }
                    // Keep app/* files together to avoid circular dependency issues
                    // (getGalaxyInstance is re-exported through app/index.js)
                    if (id.includes("/src/app/")) {
                        return "galaxy-app";
                    }
                },
            },
        },
    },
    server: {
        port: process.env.VITE_PORT || 5173,
        host: "0.0.0.0",
        proxy: {
            // Proxy everything except Vite's own routes to Galaxy backend
            "^/(?!(@|src/|node_modules/|__vite))": {
                target: process.env.GALAXY_URL || "http://127.0.0.1:8080",
                changeOrigin: !!process.env.CHANGE_ORIGIN,
                secure: process.env.CHANGE_ORIGIN ? false : true,
            },
        },
        cors: true,
        hmr: {
            protocol: "ws",
            host: "localhost",
        },
    },
    worker: {
        format: "es",
    },
});
