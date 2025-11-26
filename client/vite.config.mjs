import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import ViteYaml from "@modyfi/vite-plugin-yaml";
import vue from "@vitejs/plugin-vue2";
import { defineConfig } from "vite";
import tsconfigPaths from "vite-tsconfig-paths";

import { buildMetadataPlugin } from "./vite-plugin-build-metadata.js";
import { galaxyLegacyPlugin } from "./vite-plugin-webpack-aliases.js";

const __dirname = dirname(fileURLToPath(import.meta.url));

export default defineConfig({
    define: {
        // Make jQuery available globally for plugins and legacy code
        global: "globalThis",
        // Define build system for runtime checks
        __GALAXY_BUILD_SYSTEM__: JSON.stringify("vite"),
        // Define build timestamp
        __buildTimestamp__: JSON.stringify(new Date().toISOString()),
        // Define webpack public path as a no-op for Vite
        __webpack_public_path__: "undefined",
    },
    plugins: [
        vue(), // Vue 2.7 support
        tsconfigPaths(), // TypeScript path resolution
        ViteYaml(), // YAML file support
        galaxyLegacyPlugin(), // Handle legacy webpack-style imports
        buildMetadataPlugin(), // Generate build metadata (replaces DumpMetaPlugin)
    ],
    // resolve aliases are handled by galaxyLegacyPlugin
    css: {
        preprocessorOptions: {
            scss: {
                quietDeps: true,
                silenceDeprecations: ["mixed-decls", "import"],
                includePaths: ["src/style", "src/style/scss", "node_modules"],
            },
        },
    },
    build: {
        outDir: "dist",
        emptyOutDir: true,
        // Generate manifest.json for production
        manifest: true,
        // Disable CSS code splitting - combine all CSS into one file like webpack does
        cssCodeSplit: false,
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
