import { composeStories } from "@storybook/vue3-vite";
import { type StoryOf, useStoryMount } from "@tests/vitest/stories";
import flushPromises from "flush-promises";
import { describe, expect, it } from "vitest";

import * as stories from "./PageView.stories";

import Heading from "@/components/Common/Heading.vue";
import Markdown from "@/components/Markdown/Markdown.vue";

const composed = composeStories(stories);
const { Published, Embedded, DisplayOnly } = composed;
const mountStory = useStoryMount();

async function mountPageView(story: StoryOf<typeof composed>, props: Record<string, unknown> = {}) {
    const wrapper = mountStory(story, { props });
    await flushPromises();
    return wrapper;
}

type PageViewWrapper = Awaited<ReturnType<typeof mountPageView>>;

/** The page's Markdown, which shows the page has loaded. */
function loadedMarkdown(wrapper: PageViewWrapper) {
    const markdown = wrapper.findComponent(Markdown);
    expect(markdown.exists()).toBe(true);
    return markdown;
}

/** Headings PageView renders itself, apart from the one inside the page's Markdown. */
function ownHeadings(wrapper: PageViewWrapper) {
    const markdown = loadedMarkdown(wrapper);
    return wrapper.findAllComponents(Heading).filter((heading) => !markdown.element.contains(heading.element));
}

describe("PageView", () => {
    describe("default mode (published page with chrome)", () => {
        it("does not render embed container", async () => {
            const wrapper = await mountPageView(Published);
            loadedMarkdown(wrapper);

            expect(wrapper.find(".page-view.embed").exists()).toBe(false);
        });
    });

    describe("embed mode", () => {
        it("renders in the embed container", async () => {
            const wrapper = await mountPageView(Embedded);

            expect(wrapper.find(".page-view.embed").exists()).toBe(true);
        });
    });

    describe("displayOnly mode", () => {
        it("renders in the embed container", async () => {
            const wrapper = await mountPageView(DisplayOnly);

            expect(wrapper.find(".page-view.embed").exists()).toBe(true);
        });

        it("hides duplicate heading when displayOnly", async () => {
            // The embed shows its own, so the check below can find one.
            expect(ownHeadings(await mountPageView(Embedded, { showHeading: true }))).toHaveLength(1);

            const wrapper = await mountPageView(DisplayOnly, { showHeading: true });

            expect(ownHeadings(wrapper)).toHaveLength(0);
        });
    });
});
