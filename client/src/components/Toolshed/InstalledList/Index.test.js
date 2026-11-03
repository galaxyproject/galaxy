import { composeStories } from "@storybook/vue3-vite";
import { nth } from "@tests/vitest/helpers";
import { useStoryMount } from "@tests/vitest/stories";
import flushPromises from "flush-promises";
import { describe, expect, it } from "vitest";

import { BOWTIE2, FASTP } from "../test_fixtures";
import * as IndexStories from "./Index.stories";

import GLink from "@/components/BaseComponents/GLink.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const { FromTwoToolSheds, FromOneToolShed } = composeStories(IndexStories);
const mountStory = useStoryMount();

const SELECTORS = {
    INSTALLED_MESSAGE: ".installed-message",
    REPOSITORY_NAME: ".name",
    BADGE: ".badge",
    COLUMN_HEADER: "thead th",
};

async function mountInstalledList(story) {
    const wrapper = mountStory(story);
    await flushPromises();
    return wrapper;
}

function columnHeaders(wrapper) {
    return wrapper.findAll(SELECTORS.COLUMN_HEADER).map((th) => th.text());
}

describe("InstalledList", () => {
    it("shows a loading message until the installed repositories arrive", async () => {
        const wrapper = mountStory(FromTwoToolSheds);

        expect(wrapper.findComponent(LoadingSpan).props("message")).toBe("Loading installed repositories");

        await flushPromises();

        expect(wrapper.findComponent(LoadingSpan).exists()).toBe(false);
        expect(wrapper.find(SELECTORS.INSTALLED_MESSAGE).exists()).toBe(true);
    });

    it("lists the installed repositories and flags ones with a newer version", async () => {
        const wrapper = await mountInstalledList(FromTwoToolSheds);

        expect(wrapper.find(SELECTORS.INSTALLED_MESSAGE).text()).toBe("2 repositories installed on this instance.");
        const names = wrapper.findAll(SELECTORS.REPOSITORY_NAME);
        expect(names.length).toBe(2);
        expect(nth(names, 0).text()).toBe(BOWTIE2.name);
        expect(nth(names, 1).text()).toBe(FASTP.name);

        // The installation-progress toggle, then one link per repository.
        const links = wrapper.findAllComponents(GLink);
        expect(links.length).toBe(3);
        expect(nth(links, 1).find(SELECTORS.BADGE).text()).toBe("Newer version available!");
        expect(nth(links, 2).find(SELECTORS.BADGE).exists()).toBe(false);
    });

    it("adds a Tool Shed column when repositories come from more than one Tool Shed", async () => {
        const wrapper = await mountInstalledList(FromTwoToolSheds);

        expect(columnHeaders(wrapper)).toContain("Tool Shed");
    });

    it("has no Tool Shed column when every repository comes from one Tool Shed", async () => {
        const wrapper = await mountInstalledList(FromOneToolShed);

        expect(columnHeaders(wrapper)).toContain("Name");
        expect(columnHeaders(wrapper)).not.toContain("Tool Shed");
    });
});
