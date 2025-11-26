import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue2";
import tsconfigPaths from "vite-tsconfig-paths";
import ViteYaml from "@modyfi/vite-plugin-yaml";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { galaxyLegacyPlugin } from "./vite-plugin-webpack-aliases.js";
import { buildMetadataPlugin } from "./vite-plugin-build-metadata.js";

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
        rollupOptions: {
            input: {
                // Entry points that will be referenced in templates
                analysis: resolve(__dirname, "src/entry/analysis/index.ts"),
                generic: resolve(__dirname, "src/entry/generic.js"),
            },
            output: {
                entryFileNames: "[name].bundled.js",
                chunkFileNames: "[name]-[hash].js",
                assetFileNames: "[name]-[hash].[ext]",
            },
        },
    },
    server: {
        port: process.env.VITE_PORT || 5173,
        cors: true,
        hmr: {
            // Ensure HMR works correctly
            protocol: "ws",
            host: "localhost",
        },
        // Allow Galaxy to access Vite dev server
        headers: {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        },
    },
    worker: {
        format: "es",
    },
});
