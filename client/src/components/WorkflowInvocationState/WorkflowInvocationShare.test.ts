import { composeStories } from "@storybook/vue3-vite";
import { type StoryOf, useStoryMount } from "@tests/vitest/stories";
import type { VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { clickModalButton } from "@/components/BaseComponents/test-utils";
import { clearRaisedToasts, raisedToasts } from "@/composables/__mocks__/toast";

import * as WorkflowInvocationShareStories from "./WorkflowInvocationShare.stories";

import WorkflowInvocationShare from "./WorkflowInvocationShare.vue";
import GModal from "@/components/BaseComponents/GModal.vue";

vi.mock("@/composables/toast");

const stories = composeStories(WorkflowInvocationShareStories);
const mountStory = useStoryMount();

const SHARE_SUCCESS_MSG = "Workflow and history are now shareable.";
const CLIPBOARD_MSG = "The link to the invocation has been copied to your clipboard.";
const INVOCATION_LINK = expect.stringMatching(
    new RegExp(`/workflows/invocations/${stories.NotYetShareable.args.invocationId}$`),
);

const SELECTORS = {
    SHARE_ICON_BUTTON: "[data-button-share]",
} as const;

const writeText = vi.fn();
Object.defineProperty(navigator, "clipboard", {
    writable: true,
    configurable: true,
    value: { writeText },
});

/** Mounts a story and waits for the page to load the invocation's workflow and history. */
async function mountShare(story: StoryOf<typeof stories>) {
    const wrapper = mountStory(story);
    await vi.waitFor(() => expect(wrapper.findComponent(WorkflowInvocationShare).exists()).toBe(true));
    await flushPromises();
    return wrapper;
}

async function clickShareIcon(wrapper: VueWrapper) {
    await wrapper.find(SELECTORS.SHARE_ICON_BUTTON).trigger("click");
    await flushPromises();
}

describe("WorkflowInvocationShare", () => {
    beforeEach(() => {
        clearRaisedToasts();
        writeText.mockReset();
        writeText.mockResolvedValue(undefined);
    });

    it("opens the modal with the expected history and workflow information", async () => {
        const wrapper = await mountShare(stories.NotYetShareable);
        expect(wrapper.findComponent(GModal).props("show")).toBe(false);

        await clickShareIcon(wrapper);

        const modal = wrapper.findComponent(GModal);
        expect(modal.props("show")).toBe(true);
        expect(modal.text()).toContain('"RNA-seq alignment"');
        expect(modal.text()).toContain('"RNA-seq run"');
    });

    it("shares the workflow and history when the share button is clicked, and copies link", async () => {
        const wrapper = await mountShare(stories.NotYetShareable);
        await clickShareIcon(wrapper);

        await clickModalButton(wrapper, "Share");

        expect(wrapper.findComponent(GModal).props("show")).toBe(false);
        expect(raisedToasts()).toEqual([
            { variant: "success", message: SHARE_SUCCESS_MSG },
            { variant: "info", message: CLIPBOARD_MSG },
        ]);
        expect(writeText).toHaveBeenCalledExactlyOnceWith(INVOCATION_LINK);
    });

    it.each([
        { condition: "the user owns neither the workflow nor the history", story: stories.SomeoneElsesInvocation },
        { condition: "the user owns the workflow but not the history", story: stories.SomeoneElsesHistory },
        { condition: "the user owns the history but not the workflow", story: stories.SomeoneElsesWorkflow },
    ])("renders nothing when $condition", async ({ story }) => {
        const wrapper = await mountShare(story);

        expect(wrapper.find(SELECTORS.SHARE_ICON_BUTTON).exists()).toBe(false);
        expect(wrapper.findComponent(GModal).exists()).toBe(false);
    });

    it("just copies link and does not open modal if both workflow and history are already shareable", async () => {
        const wrapper = await mountShare(stories.AlreadyShareable);
        expect(wrapper.findComponent(GModal).props("show")).toBe(false);

        await clickShareIcon(wrapper);

        expect(wrapper.findComponent(GModal).props("show")).toBe(false);
        expect(raisedToasts()).toEqual([{ variant: "info", message: CLIPBOARD_MSG }]);
        expect(writeText).toHaveBeenCalledExactlyOnceWith(INVOCATION_LINK);
    });
});
