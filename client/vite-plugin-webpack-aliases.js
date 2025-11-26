import path from "path";
import { fileURLToPath } from "url";

import { extensions, getViteAliases } from "./build-config.shared.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/**
 * Vite plugin for Galaxy's legacy module resolution
 * Uses shared configuration with webpack
 */
export function galaxyLegacyPlugin() {
    return {
        name: "vite-plugin-galaxy-legacy",

        config: () => {
            // Get base aliases
            const aliases = getViteAliases();

            // Add jquery alias for Vite-compatible version
            // This should override the one from shared config which was skipped
            aliases.unshift({
                find: /^jquery$/,
                replacement: path.join(__dirname, "src/libs/jquery.custom.vite.js"),
            });

            // Also override jqueryVendor to point to the actual jQuery module
            aliases.unshift({
                find: /^jqueryVendor$/,
                replacement: "jquery",
            });

            return {
                resolve: {
                    alias: aliases,
                    extensions,
                },

                optimizeDeps: {
                    // Pre-bundle problematic CommonJS dependencies
                    include: ["store", "jquery-migrate", "underscore", "backbone", "jqueryVendor"],

                    // Fix CommonJS global references
                    esbuildOptions: {
                        define: {
                            global: "globalThis",
                        },
                    },
                },
            };
        },

        // Custom resolver for edge cases
        resolveId(id) {
            // Special handling for popper.js
            if (id === "popper.js") {
                return { id: "popper.js/dist/esm/popper.js", external: false };
            }

            return null;
        },
    };
}
