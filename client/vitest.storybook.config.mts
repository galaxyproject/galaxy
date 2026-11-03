import { storybookTest } from "@storybook/addon-vitest/vitest-plugin";
import { playwright } from "@vitest/browser-playwright";
import { defineConfig, mergeConfig } from "vitest/config";

import { adaptViteConfig } from "./.storybook/viteConfig";
import appViteConfig from "./vite.config.mjs";

/**
 * Runs every story as a test in Chromium: each must render, and a story's play
 * function holds its interactions and assertions. Kept apart from the happy-dom
 * unit project, whose test-only aliases and mocks (vitest.config.mts) don't apply here.
 * No setup file: storybookTest() applies the preview's annotations itself.
 */
export default defineConfig(async (env) =>
    // "serve", as for the dev server, so galaxy-api-client resolves to its source.
    mergeConfig(await adaptViteConfig(appViteConfig({ ...env, command: "serve" })), {
        plugins: [storybookTest({ configDir: ".storybook" })],
        test: {
            name: "storybook",
            browser: {
                enabled: true,
                headless: true,
                // A fixed zone keeps time-relative stories stable across DST changes.
                provider: playwright({ contextOptions: { timezoneId: "UTC" } }),
                instances: [{ browser: "chromium" }],
            },
        },
    }),
);
