import { composeStories } from "@storybook/vue3-vite";
import { getLocalVue } from "@tests/vitest/helpers";
import { useStoryMount } from "@tests/vitest/stories";
import { mount, type VueWrapper } from "@vue/test-utils";
import { describe, expect, it, onTestFinished } from "vitest";

import * as CollectionProgressStories from "./CollectionProgress.stories";
import { jobStateSummary } from "./test_fixtures";

import CollectionProgress from "./CollectionProgress.vue";

const stories = composeStories(CollectionProgressStories);
const mountStory = useStoryMount();

/** Rendered progress bars as `{ <bootstrap variant>: <aria-valuenow> }`. */
function renderedBars(wrapper: VueWrapper) {
    return Object.fromEntries(
        wrapper.findAll(".progress .progress-bar").map((bar) => {
            const variant = bar.classes().find((name) => name.startsWith("bg-"))!;
            return [variant.replace("bg-", ""), bar.attributes("aria-valuenow")];
        }),
    );
}

describe("CollectionProgress", () => {
    it.each([
        { name: "running jobs as a warning bar", story: stories.Running, bars: { warning: "3" } },
        {
            name: "failed, ok and running jobs as separate bars",
            story: stories.FailedOkAndRunning,
            bars: { danger: "1", success: "1", warning: "3" },
        },
        { name: "queued jobs as a secondary bar", story: stories.Queued, bars: { secondary: "3" } },
    ])("shows $name", ({ story, bars }) => {
        const wrapper = mountStory(story);

        expect(renderedBars(wrapper)).toEqual(bars);
    });

    it("updates the bars as job states change", async () => {
        // A plain mount, as a story can't change a live mount's props.
        const wrapper = mount(CollectionProgress, {
            props: { summary: stories.Running.args.summary! },
            global: getLocalVue(),
        });
        onTestFinished(() => wrapper.unmount());
        expect(renderedBars(wrapper)).toEqual({ warning: "3" });

        await wrapper.setProps({ summary: jobStateSummary({ all_jobs: 3, running: 1, ok: 2 }) });

        expect(renderedBars(wrapper)).toEqual({ success: "2", warning: "1" });
    });

    it("hides the progress bar once every job is terminal", () => {
        const wrapper = mountStory(stories.AllOk);

        expect(wrapper.find(".progress").exists()).toBe(false);
    });
});
