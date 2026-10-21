import { composeStories } from "@storybook/vue3-vite";
import { getFakeAnonymousUser } from "@tests/test-data";
import { type StoryMountOptions, type StoryOf, useStoryMount } from "@tests/vitest/stories";
import type { VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { submitToolInstallationRequest } from "@/api/notifications";
import { clickModalButton } from "@/components/BaseComponents/test-utils";
import { useConfigStore } from "@/stores/configurationStore";
import { useUserStore } from "@/stores/userStore";

import * as WorkflowMissingToolsRequestStories from "./WorkflowMissingToolsRequest.stories";

// Spied, not replaced: requests still reach the stories' handlers.
vi.mock("@/api/notifications", { spy: true });

const submitRequestMock = vi.mocked(submitToolInstallationRequest);

const stories = composeStories(WorkflowMissingToolsRequestStories);
const mountStory = useStoryMount();

const WORKFLOW_ID = stories.MissingTools.args.workflowId;
const MISSING_TOOL_IDS = stories.MissingTools.args.missingToolIds!;

// The requested-tool entries the component derives from MISSING_TOOL_IDS.
const EXPECTED_REQUESTED_TOOLS = [
    { tool_shed_id: "toolshed.g2.bx.psu.edu/repos/devteam/bwa", name: "bwa", requested_version: "0.7.17" },
    { tool_shed_id: "toolshed.g2.bx.psu.edu/repos/devteam/samtools", name: "samtools", requested_version: "1.13" },
];

const SIXTY_TOOL_IDS = stories.OverRequestLimit.args.missingToolIds!;

const SELECTORS = {
    REQUEST_BUTTON: "[data-testid='request-install-btn']",
    ROOT: ".workflow-missing-tools-request",
};

const SEND_BUTTON_TEXT = "Send Request";

/** Mounts a story once the config the button depends on has loaded. */
async function mountRequest(story: StoryOf<typeof stories>, options?: StoryMountOptions) {
    const wrapper = mountStory(story, options);
    await vi.waitFor(() => expect(useConfigStore().isLoaded).toBe(true));
    await flushPromises();
    return wrapper;
}

async function openRequestModal(wrapper: VueWrapper) {
    await wrapper.find(SELECTORS.REQUEST_BUTTON).trigger("click");
    await flushPromises();
}

async function sendRequest(wrapper: VueWrapper) {
    await openRequestModal(wrapper);
    await clickModalButton(wrapper, SEND_BUTTON_TEXT);
}

function sentRequest() {
    expect(submitRequestMock).toHaveBeenCalledOnce();
    const [request] = submitRequestMock.mock.lastCall ?? [];
    if (!request) {
        throw new Error("no installation request was sent");
    }
    return request;
}

describe("WorkflowMissingToolsRequest", () => {
    beforeEach(() => {
        submitRequestMock.mockReset();
    });

    describe("request button", () => {
        it.each([
            { condition: "the feature flag is disabled", story: stories.RequestFormOff },
            {
                condition: "the notification system is off, which the request needs",
                story: stories.NotificationSystemOff,
            },
        ])("does not render when $condition", async ({ story }) => {
            const wrapper = await mountRequest(story);

            expect(wrapper.find(SELECTORS.REQUEST_BUTTON).exists()).toBe(false);
        });

        it("does not render when no tool IDs are provided", async () => {
            const wrapper = await mountRequest(stories.MissingTools, { props: { missingToolIds: [] } });

            expect(wrapper.find(SELECTORS.ROOT).exists()).toBe(false);
        });

        it("does not render when user is anonymous", async () => {
            const wrapper = await mountRequest(stories.AnonymousVisitor);

            expect(wrapper.find(SELECTORS.ROOT).exists()).toBe(false);
        });

        it("stops rendering when the current user becomes anonymous", async () => {
            const wrapper = await mountRequest(stories.MissingTools);
            // A page that hasn't loaded the user yet still shows the button.
            useUserStore().currentUser = null;
            await flushPromises();
            expect(wrapper.find(SELECTORS.REQUEST_BUTTON).exists()).toBe(true);

            useUserStore().currentUser = getFakeAnonymousUser();
            await flushPromises();

            expect(wrapper.find(SELECTORS.ROOT).exists()).toBe(false);
        });
    });

    describe("sending the request", () => {
        it("calls submitToolInstallationRequest with correct payload on confirm", async () => {
            const wrapper = await mountRequest(stories.MissingTools);

            await sendRequest(wrapper);

            expect(sentRequest()).toEqual({
                tools: EXPECTED_REQUESTED_TOOLS,
                workflow_id: WORKFLOW_ID,
                additional_remarks: expect.any(String),
            });
        });

        it("additional_remarks describes the workflow context without repeating the structured tool ids", async () => {
            const wrapper = await mountRequest(stories.MissingTools);

            await sendRequest(wrapper);

            const remarks = sentRequest().additional_remarks;
            expect(remarks).toContain("required by this workflow");
            for (const id of MISSING_TOOL_IDS) {
                expect(remarks).not.toContain(id);
            }
        });

        it("caps the request at 50 tools and notes the truncation in the remarks", async () => {
            const wrapper = await mountRequest(stories.OverRequestLimit);

            await sendRequest(wrapper);

            const { tools, additional_remarks } = sentRequest();
            expect(tools.map(({ name }) => name)).toEqual(SIXTY_TOOL_IDS.slice(0, 50));
            expect(additional_remarks).toContain("Only the first 50 of 60 missing tools");
        });

        // A role can't tell a success alert from a danger one, so the plays leave variants here.
        it.each([
            { outcome: "a sent request", story: stories.MissingTools, variant: "success" },
            { outcome: "a refused request", story: stories.RequestFails, variant: "danger" },
        ])("shows $outcome as a $variant alert", async ({ story, variant }) => {
            const wrapper = await mountRequest(story);

            await sendRequest(wrapper);

            expect(wrapper.find(`.alert-${variant}`).exists()).toBe(true);
        });
    });
});
