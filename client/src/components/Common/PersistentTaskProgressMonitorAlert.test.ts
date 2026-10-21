import { composeStories } from "@storybook/vue3-vite";
import { type StoryOf, useStoryMount } from "@tests/vitest/stories";
import { afterEach, describe, expect, it } from "vitest";

import * as PersistentTaskProgressMonitorAlertStories from "./PersistentTaskProgressMonitorAlert.stories";

import GAlert from "@/components/BaseComponents/GAlert.vue";

const stories = composeStories(PersistentTaskProgressMonitorAlertStories);
const mountStory = useStoryMount();

const selectors = {
    ProgressAlert: ".progress-monitor-alert",
} as const;

/** Mounts a story and returns its one alert, after checking the monitor shows anything at all. */
function mountAlert(story: StoryOf<typeof stories>) {
    const wrapper = mountStory(story);
    expect(wrapper.find(selectors.ProgressAlert).exists()).toBe(true);
    return { wrapper, alert: wrapper.getComponent(GAlert) };
}

// The stories' plays read each alert's text and the download link. A play can tell a
// `status` alert from an `alert` one by role, but not info from success or danger from warning.
describe("PersistentTaskProgressMonitorAlert.vue", () => {
    afterEach(() => {
        localStorage.clear();
    });

    it("does not render when no monitoring data is available", () => {
        const wrapper = mountStory(stories.NoTaskStarted);
        expect(wrapper.find(selectors.ProgressAlert).exists()).toBe(false);
    });

    it.each([
        { story: stories.InProgress, state: "in progress", variant: "info" },
        { story: stories.Completed, state: "completed", variant: "success" },
        { story: stories.DownloadReady, state: "completed with a download", variant: "success" },
        { story: stories.Failed, state: "failed", variant: "danger" },
        // Expired even though the last status seen was running.
        { story: stories.Expired, state: "expired", variant: "warning" },
    ])("renders a $variant alert when the task has $state", ({ story, variant }) => {
        const { alert } = mountAlert(story);

        expect(alert.props("variant")).toBe(variant);
    });
});
