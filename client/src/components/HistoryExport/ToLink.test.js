import { composeStories } from "@storybook/vue3-vite";
import { deferred } from "@tests/vitest/deferred";
import { useStoryMount } from "@tests/vitest/stories";
import flushPromises from "flush-promises";
import { afterEach, describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import { waitOnJob } from "@/components/JobStates/wait";

import { EXPORT_JOB_ID, EXPORTED_HISTORY_ID } from "./test_fixtures";
import * as ToLinkStories from "./ToLink.stories";

import LoadingSpan from "@/components/LoadingSpan.vue";

const stories = composeStories(ToLinkStories);
const mountStory = useStoryMount();
const { server, http } = useServerMock();

vi.mock("@/components/JobStates/wait", () => ({
    waitOnJob: vi.fn(),
}));

afterEach(() => {
    vi.mocked(waitOnJob).mockReset();
});

describe("ToLink.vue", () => {
    async function mountAndLoadExports(story) {
        const wrapper = mountStory(story);
        await wrapper.vm.$nextTick();
        expect(wrapper.findComponent(LoadingSpan).exists()).toBeTruthy();
        expect(wrapper.findComponent(LoadingSpan).props("message")).toContain("Loading history export information");
        await flushPromises();
        return wrapper;
    }

    it("should display a link if no exports ever generated", async () => {
        const wrapper = await mountAndLoadExports(stories.NoExports);
        const exportLink = wrapper.find(".export-link");
        expect(exportLink).toBeTruthy();
        expect(exportLink.exists()).toBe(true);
    });

    it("should start polling if latest export is preparing", async () => {
        const jobCompletion = deferred();
        vi.mocked(waitOnJob).mockReturnValue(jobCompletion.promise);
        try {
            await mountAndLoadExports(stories.Preparing);
            expect(jobCompletion.resolve).toBeTruthy();
            expect(waitOnJob).toHaveBeenCalledExactlyOnceWith(EXPORT_JOB_ID);
        } finally {
            // The completed job reloads exports; return a settled history before unmount.
            server.use(http.untyped.get(`/api/histories/${EXPORTED_HISTORY_ID}/exports`, () => HttpResponse.json([])));
            jobCompletion.resolve();
            await flushPromises();
        }
    });
});
