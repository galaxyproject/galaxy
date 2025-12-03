import { extensions, getViteAliases } from "./build-config.shared.js";

/**
 * Vite plugin for Galaxy's legacy module resolution
 */
export function galaxyLegacyPlugin() {
    return {
        name: "vite-plugin-galaxy-legacy",

        config: () => {
            const aliases = getViteAliases();

            return {
                resolve: {
                    alias: aliases,
                    extensions,
                },

                optimizeDeps: {
                    // Pre-bundle problematic CommonJS dependencies
                    include: ["store", "jquery-migrate", "underscore", "backbone"],

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
