import { composeStories } from "@storybook/vue3-vite";
import { createTestRouter } from "@tests/vitest/helpers";
import { useStoryMount } from "@tests/vitest/stories";
import flushPromises from "flush-promises";
import { describe, expect, it } from "vitest";

import * as ToolCardStories from "./ToolCard.stories";

const stories = composeStories(ToolCardStories);
const mountStory = useStoryMount();

const SELECTORS = {
    TITLE: "h1",
    DESCRIPTION: "span[itemprop='description']",
    OPTIONS_DROPDOWN: ".tool-dropdown",
    OPTION: ".dropdown-item",
    BACKDROP: ".portlet-backdrop",
    NEWER_VERSION_BADGE: "[data-description='newer tool version']",
    RUN_TOOL_BUTTON: "[data-description='run tool button']",
};

/** Mounts a story and waits for the configuration the card waits on. */
async function mountToolCard(story, options) {
    const wrapper = mountStory(story, options);
    await flushPromises();
    return wrapper;
}

describe("ToolCard", () => {
    it("shows the tool's title and description", async () => {
        const wrapper = await mountToolCard(stories.LatestVersion);

        expect(wrapper.find(SELECTORS.TITLE).text()).toBe("FastQC");
        expect(wrapper.find(SELECTORS.DESCRIPTION).text()).toBe("Read Quality reports");
    });

    it("offers an admin five tool options", async () => {
        const wrapper = await mountToolCard(stories.LatestVersion);

        const options = wrapper.find(SELECTORS.OPTIONS_DROPDOWN);
        expect(options.attributes("title")).toBe("Options");
        expect(options.findAll(SELECTORS.OPTION)).toHaveLength(5);
    });

    it("covers the card with a backdrop while disabled", async () => {
        const wrapper = await mountToolCard(stories.WithRunButton);
        expect(wrapper.findAll(SELECTORS.BACKDROP)).toHaveLength(0);

        await wrapper.find(SELECTORS.RUN_TOOL_BUTTON).trigger("click");

        expect(wrapper.findAll(SELECTORS.BACKDROP)).toHaveLength(1);
    });

    it("shows a newer version badge that navigates to the latest version", async () => {
        const router = createTestRouter();
        const wrapper = await mountToolCard(stories.NewerVersionAvailable, { router });

        const badge = wrapper.find(SELECTORS.NEWER_VERSION_BADGE);
        expect(badge.text()).toBe("Newer version available");

        await badge.trigger("click");
        await flushPromises();

        expect(router.currentRoute.value.fullPath).toBe(
            "/?tool_id=toolshed.g2.bx.psu.edu%2Frepos%2Fdevteam%2Ffastqc%2Ffastqc%2F0.73%2Bgalaxy0&version=latest",
        );
    });

    it("offers a single focusable toggle for each tool menu", async () => {
        const wrapper = await mountToolCard(stories.LatestVersion);
        for (const menu of [".tool-dropdown", ".tool-versions"]) {
            const toggle = wrapper.get(`${menu} button.dropdown-toggle`);
            expect(toggle.find("button, a, [tabindex]").exists()).toBe(false);
            expect(toggle.attributes("aria-label")).toBeTruthy();
            await toggle.trigger("keydown", { key: "ArrowDown" });
            await flushPromises();
            expect(toggle.attributes("aria-expanded")).toBe("true");
            await toggle.trigger("keydown", { key: "Escape" });
        }
    });

    it.each([
        { scenario: "the latest version in its lineage", story: "LatestVersion" },
        { scenario: "a single-version tool", story: "SingleVersion" },
    ])("shows no newer version badge for $scenario", async ({ story }) => {
        const wrapper = await mountToolCard(stories[story]);
        expect(wrapper.find(SELECTORS.TITLE).text()).toBe("FastQC");

        expect(wrapper.find(SELECTORS.NEWER_VERSION_BADGE).exists()).toBe(false);
    });
});
