import type { StorybookConfig } from "@storybook/vue3-vite";

import { adaptViteConfig } from "./viteConfig.ts";

const config: StorybookConfig = {
    // vue-docgen-api can't parse the BaseComponents wrappers around galaxy-ui and
    // fails the module; no autodocs/controls inference until vue-component-meta is tried.
    framework: { name: "@storybook/vue3-vite", options: { docgen: false } },
    addons: ["msw-storybook-addon", "@storybook/addon-vitest"],
    stories: ["../src/**/*.stories.ts"],
    staticDirs: ["./public"],
    core: { disableTelemetry: true },
    viteFinal: adaptViteConfig,
};

export default config;
