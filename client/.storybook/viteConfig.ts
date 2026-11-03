import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import type { InlineConfig } from "vite";

const clientDir = resolve(dirname(fileURLToPath(import.meta.url)), "..");

const DROPPED_PLUGINS = [
    // Only make sense for the Galaxy-served app (vite.config.mjs).
    "galaxy-dev-server",
    "vite-plugin-build-metadata",
    // Aliases "vue" to plain Vue 3; Galaxy's components (and bootstrap-vue) need
    // the compat build the app runs on.
    "storybook:vue-template-compilation",
];

/**
 * Adapts the app's vite.config.mjs to serve stories, both for Storybook itself
 * and for the vitest project that runs stories as browser tests.
 */
export async function adaptViteConfig(viteConfig: InlineConfig): Promise<InlineConfig> {
    const plugins = (await Promise.all((viteConfig.plugins ?? []).flat())).flat();
    viteConfig.plugins = plugins.filter(
        (plugin) => !(plugin && "name" in plugin && DROPPED_PLUGINS.includes(plugin.name)),
    );
    // vite.config.mjs aliases "vue" to "@vue/compat"; use its full build (as
    // vitest.config.mts does) so story decorators may use templates.
    const aliases = viteConfig.resolve?.alias ?? [];
    const aliasList = Array.isArray(aliases)
        ? aliases
        : Object.entries(aliases).map(([find, replacement]) => ({ find, replacement }));
    viteConfig.resolve = {
        ...viteConfig.resolve,
        alias: [
            { find: /^vue$/, replacement: resolve(clientDir, "node_modules/@vue/compat/dist/vue.esm-bundler.js") },
            // The app picks its build config by NODE_ENV, and vitest's "test" has none.
            // Stories have no Galaxy build behind them, so use the testing one.
            { find: /^config$/, replacement: resolve(clientDir, "src/config/testing.js") },
            ...aliasList.filter((alias) => alias.find !== "vue"),
        ],
    };
    // No Galaxy server behind stories; API calls are answered by MSW.
    delete viteConfig.server?.proxy;
    if (viteConfig.build) {
        delete viteConfig.build.rolldownOptions;
        viteConfig.build.manifest = false;
    }
    return viteConfig;
}
