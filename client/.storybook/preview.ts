import "@/compat-config";
// Match Galaxy startup for components using Bootstrap data-toggle controls.
import "bootstrap";
// The app's global styles: src/onload/index.js and App.vue's unscoped <style>.
import "@/style/scss/base.scss";
import "@/style/scss/custom_theme_variables.scss";
import "@fontsource/atkinson-hyperlegible";
import "@fontsource/atkinson-hyperlegible/700.css";
// Imported by a few admin/library components; the app bundles all CSS into one
// file (cssCodeSplit: false), so every multiselect gets it there.
import "vue-multiselect/dist/vue-multiselect.min.css";

import type { Preview } from "@storybook/vue3-vite";
import { setup } from "@storybook/vue3-vite";
import { mswLoader } from "msw-storybook-addon/csf3";
import { createPinia } from "pinia";
import { createMemoryHistory, createRouter } from "vue-router";

import { appHandlers } from "@/api/client/__mocks__/http";
import { installAppPlugins } from "@/utils/mountVueComponent";

import { failOnUnmockedRequests, resetUnmockedRequests, setupStoryWorker } from "./msw";

// Components may render router links; no route needs to resolve to a real page.
const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/:pathMatch(.*)*", component: { render: () => null } }],
});

setup((app) => {
    app.use(createPinia());
    app.use(router);
    installAppPlugins(app);
});

const preview: Preview = {
    loaders: [mswLoader(setupStoryWorker)],
    beforeEach: resetUnmockedRequests,
    afterEach: failOnUnmockedRequests,
    // Named, so a story's own handlers merge with these and replace one by name.
    parameters: {
        msw: { handlers: appHandlers },
        a11y: {
            // Include body-level teleports (dialogs, menus and tooltips).
            context: "body",
            test: "error",
            options: {
                // runOnly replaces axe's defaults; retain those and add WCAG 2.2 AA.
                runOnly: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "best-practice", "wcag22aa"],
            },
        },
        viewport: {
            options: {
                galaxyDesktop: { name: "Galaxy desktop", styles: { width: "1280px", height: "900px" } },
                galaxyPanel: { name: "Galaxy narrow panel", styles: { width: "400px", height: "900px" } },
                galaxyMobile: { name: "Galaxy mobile", styles: { width: "375px", height: "812px" } },
            },
        },
    },
};

export default preview;
