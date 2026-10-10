import { composeStories } from "@storybook/vue3-vite";
import { type StoryOf, useStoryMount } from "@tests/vitest/stories";
import { afterEach, describe, expect, it } from "vitest";

import * as PersistentTaskProgressMonitorAlertStories from "./PersistentTaskProgressMonitorAlert.stories";

import GAlert from "@/components/BaseComponents/GAlert.vue";

const stories = composeStories(PersistentTaskProgressMonitorAlertStories);
const mountStory = useStoryMount();

const selectors = {
    ProgressAlert: ".progress-monitor-alert",
    DownloadLink: ".download-link",
} as const;

/** Mounts a story and returns its one alert, after checking the monitor shows anything at all. */
function mountAlert(story: StoryOf<typeof stories>) {
    const wrapper = mountStory(story);
    expect(wrapper.find(selectors.ProgressAlert).exists()).toBe(true);
    return { wrapper, alert: wrapper.getComponent(GAlert) };
}

describe("PersistentTaskProgressMonitorAlert.vue", () => {
    afterEach(() => {
        localStorage.clear();
    });

    it("does not render when no monitoring data is available", () => {
        const wrapper = mountStory(stories.NoTaskStarted);
        expect(wrapper.find(selectors.ProgressAlert).exists()).toBe(false);
    });

    it("renders in progress when monitoring data is available and in progress", () => {
        const { alert } = mountAlert(stories.InProgress);

        expect(alert.props("variant")).toBe("info");
        expect(alert.text()).toContain("Task is in progress");
    });

    it("renders completed when monitoring data is available and completed", () => {
        const { alert } = mountAlert(stories.Completed);

        expect(alert.props("variant")).toBe("success");
        expect(alert.text()).toContain("Task completed");
    });

    it("renders failed when monitoring data is available and failed", () => {
        const { alert } = mountAlert(stories.Failed);

        expect(alert.props("variant")).toBe("danger");
        expect(alert.text()).toContain("Task failed");
        expect(alert.text()).toContain("Reason: The remote file source rejected the upload");
    });

    it("renders a link to download the task result when completed and task type is 'short_term_storage'", () => {
        const { wrapper, alert } = mountAlert(stories.DownloadReady);

        expect(alert.props("variant")).toBe("success");

        const downloadLink = wrapper.find(selectors.DownloadLink);
        expect(downloadLink.exists()).toBe(true);
        expect(downloadLink.text()).toContain("Download here");
        expect(downloadLink.attributes("href")).toBe("/api/short_term_storage/c94e7b12-05a3-4d8e-b6f1-7a2d9e3c4b58");
    });

    it("does not render a link to download the task result when completed and task type is 'task'", () => {
        const { wrapper, alert } = mountAlert(stories.Completed);

        expect(alert.props("variant")).toBe("success");
        expect(alert.text()).not.toContain("Download here");
        expect(wrapper.find(selectors.DownloadLink).exists()).toBe(false);
    });

    it("should render a warning alert when the task has expired even if the status is running", () => {
        const { alert } = mountAlert(stories.Expired);

        expect(alert.props("variant")).toBe("warning");
        expect(alert.text()).toContain("The export task has expired and the result is no longer available");
    });
});
