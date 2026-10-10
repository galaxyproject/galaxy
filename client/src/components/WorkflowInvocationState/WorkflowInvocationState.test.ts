import { createTestingPinia } from "@pinia/testing";
import { composeStories } from "@storybook/vue3-vite";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { type StoryOf, useStoryMount } from "@tests/vitest/stories";
import { mount, type VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it, onTestFinished, vi } from "vitest";

import { useInvocationStore } from "@/stores/invocationStore";

import * as WorkflowInvocationStateStories from "./WorkflowInvocationState.stories";

import WorkflowInvocationOverview from "./WorkflowInvocationOverview.vue";
import WorkflowInvocationState from "./WorkflowInvocationState.vue";
import GAlert from "@/components/BaseComponents/GAlert.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const stories = composeStories(WorkflowInvocationStateStories);
const mountStory = useStoryMount();

const selectors = {
    debugTab: ".invocation-debug-tab",
    reportTab: ".invocation-report-tab",
    exportTab: ".invocation-export-tab",
};

/**
 * Mounts a story once its invocation is loaded and the page's own fetches have settled, and returns
 * the invocation store the page polls. The story preloads through the store's getters, whose fetches
 * don't reach the action spies, so the spies count only what the page asks for.
 */
async function mountInvocation(story: StoryOf<typeof stories>) {
    // happy-dom has no canvas for the graph's minimap to draw on.
    const wrapper = mountStory(story, { global: { stubs: { WorkflowMinimap: true } } });
    await vi.waitFor(() => expect(wrapper.findComponent(WorkflowInvocationState).exists()).toBe(true));
    const invocationStore = useInvocationStore();
    await Promise.all(vi.mocked(invocationStore.fetchInvocationById).mock.results.map((result) => result.value));
    await flushPromises();
    return { wrapper, invocationStore };
}

/**
 * Mounts the page for an invocation the store can't provide, with the store's fetch faked by
 * `fetchInvocationById`. The real store keeps a failed fetch's error instead of throwing it, and
 * stores whatever it fetched, so these states have no story.
 */
async function mountWithoutInvocation(invocationId: string, fetchInvocationById?: () => unknown) {
    const pinia = createTestingPinia({ createSpy: vi.fn });
    const invocationStore = useInvocationStore(pinia);
    // @ts-expect-error testing pinia makes getters writable
    invocationStore.getInvocationById = () => null;
    // @ts-expect-error testing pinia makes getters writable
    invocationStore.getInvocationJobsSummaryById = () => null;
    // @ts-expect-error testing pinia makes getters writable
    invocationStore.isLoadingInvocation = (id: string) => id === "retrying-invocation";
    if (fetchInvocationById) {
        vi.mocked(invocationStore.fetchInvocationById).mockImplementation(fetchInvocationById as never);
    }
    const wrapper = mount(WorkflowInvocationState as object, {
        props: { invocationId },
        global: withPlugins(getLocalVue(), pinia),
    });
    onTestFinished(() => wrapper.unmount());
    await flushPromises();
    return { wrapper, invocationStore };
}

/** The terminal state the component reports to its overview */
function overviewTerminalState(wrapper: VueWrapper) {
    return wrapper.findComponent(WorkflowInvocationOverview).props("invocationAndJobTerminal");
}

/** The link of the nav item a tab selector names */
function tabLink(wrapper: VueWrapper, selector: string) {
    return wrapper.find(`${selector} .nav-link`);
}

describe("WorkflowInvocationState terminal state and polling", () => {
    it("reports a scheduled invocation with terminal jobs as terminal and fetches it once without its jobs summary", async () => {
        const { wrapper, invocationStore } = await mountInvocation(stories.Completed);

        expect(overviewTerminalState(wrapper)).toBe(true);
        expect(invocationStore.fetchInvocationById).toHaveBeenCalledTimes(1);
        expect(invocationStore.fetchInvocationById).toHaveBeenCalledWith({ id: stories.Completed.args.invocationId });
        expect(invocationStore.fetchInvocationJobsSummaryForId).not.toHaveBeenCalled();
    });

    it("polls a new invocation once after the initial fetch without fetching its jobs summary", async () => {
        const { wrapper, invocationStore } = await mountInvocation(stories.SchedulingNew);

        expect(overviewTerminalState(wrapper)).toBe(false);
        expect(invocationStore.fetchInvocationById).toHaveBeenCalledTimes(2);
        expect(invocationStore.fetchInvocationJobsSummaryForId).not.toHaveBeenCalled();
    });

    it("polls only the jobs summary of a scheduled invocation with a running job", async () => {
        const { wrapper, invocationStore } = await mountInvocation(stories.JobRunning);

        expect(overviewTerminalState(wrapper)).toBe(false);
        expect(invocationStore.fetchInvocationById).toHaveBeenCalledTimes(1);
        expect(invocationStore.fetchInvocationJobsSummaryForId).toHaveBeenCalledTimes(1);
        expect(invocationStore.fetchInvocationJobsSummaryForId).toHaveBeenCalledWith({
            id: stories.JobRunning.args.invocationId,
        });
    });

    it("polls only the jobs summary of a scheduled invocation whose jobs are still being populated", async () => {
        const { wrapper, invocationStore } = await mountInvocation(stories.JobsBeingCreated);

        expect(overviewTerminalState(wrapper)).toBe(false);
        expect(invocationStore.fetchInvocationById).toHaveBeenCalledTimes(1);
        expect(invocationStore.fetchInvocationJobsSummaryForId).toHaveBeenCalledTimes(1);
    });

    it("shows an info alert and fetches no jobs summary when the fetched invocation is not in the store", async () => {
        const { wrapper, invocationStore } = await mountWithoutInvocation("not-fetched-invocation");

        expect(wrapper.findComponent(WorkflowInvocationOverview).exists()).toBe(false);
        expect(invocationStore.fetchInvocationById).toHaveBeenCalledTimes(1);
        expect(invocationStore.fetchInvocationJobsSummaryForId).not.toHaveBeenCalled();
        const alert = wrapper.findComponent(GAlert);
        expect(alert.props("variant")).toBe("info");
        expect(alert.find("span").text()).toBe("Invocation not found.");
    });

    it("shows the error of a failed invocation fetch as a danger alert and fetches no jobs summary", async () => {
        const { wrapper, invocationStore } = await mountWithoutInvocation("error-invocation", () => {
            throw new Error("User does not own specified item.");
        });

        expect(wrapper.findComponent(WorkflowInvocationOverview).exists()).toBe(false);
        expect(invocationStore.fetchInvocationById).toHaveBeenCalledTimes(1);
        expect(invocationStore.fetchInvocationJobsSummaryForId).not.toHaveBeenCalled();
        const alert = wrapper.findComponent(GAlert);
        expect(alert.props("variant")).toBe("danger");
        expect(alert.text()).toBe("User does not own specified item.");
    });

    it("shows the error the server returns for an invocation as a danger alert and fetches no jobs summary", async () => {
        const { wrapper, invocationStore } = await mountInvocation(stories.LoadFailed);

        expect(wrapper.findComponent(WorkflowInvocationOverview).exists()).toBe(false);
        expect(invocationStore.fetchInvocationById).toHaveBeenCalledTimes(1);
        expect(invocationStore.fetchInvocationJobsSummaryForId).not.toHaveBeenCalled();
        const alert = wrapper.findComponent(GAlert);
        expect(alert.props("variant")).toBe("danger");
        expect(alert.text()).toContain("User does not own specified item.");
    });
});

describe("WorkflowInvocationState retry state", () => {
    it("shows loading, not 'not found', while a failed fetch waits to retry", async () => {
        const { wrapper } = await mountWithoutInvocation("retrying-invocation");

        const alert = wrapper.findComponent(GAlert);
        expect(alert.props("variant")).toBe("info");
        expect(alert.findComponent(LoadingSpan).props("message")).toBe("Loading invocation");
        expect(alert.text()).not.toContain("Invocation not found.");
    });
});

describe("WorkflowInvocationState full page tabs", () => {
    it("keeps invocation actions inside a list item alongside navigation tabs", async () => {
        const { wrapper } = await mountInvocation(stories.Completed);
        const navigation = wrapper.get("ul.nav");

        expect(Array.from(navigation.element.children).every((child) => child.tagName === "LI")).toBe(true);
        expect(navigation.get("li.ml-auto").element.tagName).toBe("LI");
    });

    it("disables the Report and Export tabs of a new invocation", async () => {
        const { wrapper } = await mountInvocation(stories.SchedulingNew);

        expect(tabLink(wrapper, selectors.reportTab).attributes("aria-disabled")).toBe("true");
        expect(tabLink(wrapper, selectors.exportTab).attributes("aria-disabled")).toBe("true");
    });

    it("enables the Report and Export tabs of a scheduled invocation with terminal jobs", async () => {
        const { wrapper } = await mountInvocation(stories.Completed);

        expect(tabLink(wrapper, selectors.reportTab).attributes("aria-disabled")).toBeUndefined();
        expect(tabLink(wrapper, selectors.exportTab).attributes("aria-disabled")).toBeUndefined();
    });

    it("hides the Debug tab while an invocation with a failed job still has a running job", async () => {
        const { wrapper } = await mountInvocation(stories.JobFailedWhileAnotherRuns);

        expect(overviewTerminalState(wrapper)).toBe(false);
        expect(wrapper.find(selectors.debugTab).exists()).toBe(false);
    });

    it("shows the Debug tab once an invocation with a failed job is terminal", async () => {
        const { wrapper } = await mountInvocation(stories.JobFailed);

        expect(overviewTerminalState(wrapper)).toBe(true);
        expect(wrapper.find(selectors.debugTab).exists()).toBe(true);
    });
});
