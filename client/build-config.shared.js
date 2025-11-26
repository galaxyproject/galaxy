/**
 * Build configuration for Vite
 * Single source of truth for legacy module resolution
 */
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const scriptsBase = path.join(__dirname, "src");
const libsBase = path.join(scriptsBase, "libs");
const styleBase = path.join(scriptsBase, "style");

// Legacy exact-match aliases
export const legacyAliases = {
    // Core libraries
    jquery: path.join(libsBase, "jquery.custom.js"),
    jqueryVendor: path.join(libsBase, "jquery/jquery.js"),
    storemodern: path.join(__dirname, "node_modules/store/dist/store.modern.js"),

    // Vue
    vue: path.join(__dirname, "node_modules/vue/dist/vue.esm.js"),

    // Build config
    config: path.join(scriptsBase, "config", process.env.NODE_ENV || "development") + ".js",
    app: path.join(scriptsBase, "app.js"),
};

// Module resolution paths
export const modulePaths = [scriptsBase, "node_modules", styleBase];

// File extensions for resolution
export const extensions = [".ts", ".js", ".json", ".vue", ".scss"];

/**
 * Get Vite-format aliases (uses regex patterns for exact matches)
 */
export function getViteAliases() {
    const viteAliases = [
        // @ alias
        { find: "@", replacement: scriptsBase },
    ];

    // Add exact match patterns
    for (const [key, value] of Object.entries(legacyAliases)) {
        // Skip jquery in dev mode - handled by plugin
        if (key === "jquery" && process.env.NODE_ENV === "development") {
            continue;
        }

        viteAliases.push({
            find: new RegExp(`^${key}$`),
            replacement: path.isAbsolute(value) ? value : path.join(__dirname, value),
        });
    }

    // Add prefix patterns for legacy paths
    viteAliases.push(
        { find: /^libs\//, replacement: libsBase + "/" },
        { find: /^ui\//, replacement: path.join(scriptsBase, "ui") + "/" },
    );

    return viteAliases;
}
