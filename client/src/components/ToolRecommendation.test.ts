import { composeStories } from "@storybook/vue3-vite";
import { type StoryOf, useStoryMount } from "@tests/vitest/stories";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getDatatypesMapper } from "@/components/Datatypes";
import { getToolPredictions } from "@/components/Workflow/Editor/modules/services";

import * as componentStories from "./ToolRecommendation.stories";

import ToolRecommendation from "./ToolRecommendation.vue";

vi.mock("@/components/Datatypes", { spy: true });
vi.mock("@/components/Workflow/Editor/modules/services", { spy: true });

const stories = composeStories(componentStories);
const mountStory = useStoryMount();

describe("ToolRecommendation", () => {
    beforeEach(() => {
        vi.mocked(getToolPredictions).mockReset();
        vi.mocked(getDatatypesMapper).mockReset();
    });

    async function mountRecommendation(story: StoryOf<typeof stories> = stories.CompatibleTools) {
        const wrapper = mountStory(story).getComponent(ToolRecommendation);
        await flushPromises();
        // Wait for the real prediction and mapper promises, including the expected rejected requests.
        await Promise.allSettled(vi.mocked(getToolPredictions).mock.results.map((result) => result.value));
        await flushPromises();
        await Promise.allSettled(vi.mocked(getDatatypesMapper).mock.results.map((result) => result.value));
        await flushPromises();
        return wrapper;
    }

    it("renders compatible recommendations", async () => {
        const wrapper = await mountRecommendation();
        expect(getToolPredictions).toHaveBeenCalledWith({ tool_sequence: "cat1" });
        expect(wrapper.text()).toContain("For further analysis");
        // The concatenation root plus one child node ("Cut") rendered by d3
        expect(wrapper.findAll("g.node")).toHaveLength(2);
        expect(wrapper.text()).toContain("Cut");
    });

    it.each(["API authentication required for this request", "Network Error"])(
        "handles prediction failure: %s",
        async (message) => {
            // This endpoint permits anonymous access; retain the original synthetic authentication rejection locally.
            if (message === "API authentication required for this request") {
                vi.mocked(getToolPredictions).mockRejectedValueOnce(new Error(message));
            }
            const wrapper = await mountRecommendation(stories.PredictionNetworkFailure);
            expect(wrapper.text()).toContain("Tool recommendations could not be loaded");
            expect(wrapper.text()).toContain(message);
            expect(getDatatypesMapper).not.toHaveBeenCalled();
            expect(wrapper.findAll("g.node")).toHaveLength(0);
        },
    );

    it("handles datatype loading failure", async () => {
        // Keep the original synthetic message; the standalone story exercises the real fetch network failure.
        vi.mocked(getDatatypesMapper).mockRejectedValueOnce(new Error("Datatypes unavailable"));
        const wrapper = await mountRecommendation(stories.DatatypesNetworkFailure);
        expect(wrapper.text()).toContain("Datatypes unavailable");
        expect(wrapper.findAll("g.node")).toHaveLength(0);
    });

    it("handles an unconfigured prediction model", async () => {
        const wrapper = await mountRecommendation(stories.NoPredictionModel);
        expect(getDatatypesMapper).not.toHaveBeenCalled();
        expect(wrapper.findAll("g.node")).toHaveLength(0);
        expect(wrapper.text()).not.toContain("For further analysis");
    });
});
