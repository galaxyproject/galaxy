import { getFakeHistorySummaryExtended, getFakeRegisteredUser } from "@tests/test-data";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount, type VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__/index";
import type { StoredWorkflowDetailed } from "@/api/workflows";
import { clickModalButton } from "@/components/BaseComponents/test-utils";
import { clearRaisedToasts, raisedToasts } from "@/composables/__mocks__/toast";
import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";
import { useWorkflowStore } from "@/stores/workflowStore";

import WorkflowInvocationShare from "./WorkflowInvocationShare.vue";
import GModal from "@/components/BaseComponents/GModal.vue";

vi.mock("@/composables/toast");

const WORKFLOW_OWNER = "test-user";
const OTHER_USER = "other-user";
// `getFakeRegisteredUser` always defaults to this id, regardless of `username`
const CURRENT_USER_ID = "fake_user_id";
const OTHER_USER_ID = "other-user-id";
const INVOCATION_ID = "invocation-id";
const TEST_WORKFLOW = {
    id: "workflow-id",
    name: "workflow-name",
    owner: WORKFLOW_OWNER,
    version: 1,
    importable: false,
    published: false,
    users_shared_with: [],
    title: "workflow-title",
};
const TEST_HISTORY = {
    id: "test-history-id",
    name: "test-history-name",
    archived: false,
    user_id: CURRENT_USER_ID,
};
const TEST_HISTORY_POST_SHARE = {
    ...TEST_HISTORY,
    importable: true,
    published: false,
    users_shared_with: [],
    title: "history-title",
};
const SHARE_SUCCESS_MSG = "Workflow and history are now shareable.";
const CLIPBOARD_MSG = "The link to the invocation has been copied to your clipboard.";
const INVOCATION_LINK = expect.stringMatching(new RegExp(`/workflows/invocations/${INVOCATION_ID}$`));

const SELECTORS = {
    SHARE_ICON_BUTTON: "[data-button-share]",
} as const;

const writeText = vi.fn();
Object.defineProperty(navigator, "clipboard", {
    writable: true,
    configurable: true,
    value: { writeText },
});

const { server, http } = useServerMock();

const localVue = getLocalVue();

enableAutoUnmount(afterEach);

interface InvocationShareSetup {
    /** Whether the current user owns the invocation's workflow */
    ownsWorkflow?: boolean;
    /** Whether the current user owns the invocation's history */
    ownsHistory?: boolean;
    /** Whether the workflow and history are already accessible via link */
    bothShareable?: boolean;
}

async function mountWorkflowInvocationShare({
    ownsWorkflow = true,
    ownsHistory = true,
    bothShareable = false,
}: InvocationShareSetup = {}) {
    server.use(
        http.put("/api/workflows/{workflow_id}/enable_link_access", ({ response }) => {
            return response(200).json({ ...TEST_WORKFLOW, importable: true });
        }),
        http.put("/api/histories/{history_id}/enable_link_access", ({ response }) => {
            return response(200).json(TEST_HISTORY_POST_SHARE);
        }),
    );

    const pinia = createPinia();
    useUserStore(pinia).currentUser = getFakeRegisteredUser({ username: ownsWorkflow ? WORKFLOW_OWNER : OTHER_USER });
    useWorkflowStore(pinia).workflowsByInstanceId = {
        [TEST_WORKFLOW.id]: {
            id: TEST_WORKFLOW.id,
            name: TEST_WORKFLOW.name,
            owner: TEST_WORKFLOW.owner,
            importable: bothShareable,
        } as StoredWorkflowDetailed,
    };
    useHistoryStore(pinia).setHistory({
        ...getFakeHistorySummaryExtended({
            ...TEST_HISTORY,
            user_id: ownsHistory ? CURRENT_USER_ID : OTHER_USER_ID,
        }),
        importable: bothShareable,
    });

    const wrapper = mount(WorkflowInvocationShare, {
        props: {
            invocationId: INVOCATION_ID,
            workflowId: TEST_WORKFLOW.id,
            historyId: TEST_HISTORY.id,
        },
        global: withPlugins(localVue, pinia),
    });
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
        const wrapper = await mountWorkflowInvocationShare();
        expect(wrapper.findComponent(GModal).props("show")).toBe(false);

        await clickShareIcon(wrapper);

        const modal = wrapper.findComponent(GModal);
        expect(modal.props("show")).toBe(true);
        expect(modal.text()).toContain(TEST_WORKFLOW.name);
        expect(modal.text()).toContain(TEST_HISTORY.name);
    });

    it("shares the workflow and history when the share button is clicked, and copies link", async () => {
        const wrapper = await mountWorkflowInvocationShare();
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
        { condition: "the user owns neither the workflow nor the history", ownsWorkflow: false, ownsHistory: false },
        { condition: "the user owns the workflow but not the history", ownsWorkflow: true, ownsHistory: false },
        { condition: "the user owns the history but not the workflow", ownsWorkflow: false, ownsHistory: true },
    ])("renders nothing when $condition", async ({ ownsWorkflow, ownsHistory }) => {
        const wrapper = await mountWorkflowInvocationShare({ ownsWorkflow, ownsHistory });

        expect(wrapper.find(SELECTORS.SHARE_ICON_BUTTON).exists()).toBe(false);
        expect(wrapper.findComponent(GModal).exists()).toBe(false);
    });

    it("just copies link and does not open modal if both workflow and history are already shareable", async () => {
        const wrapper = await mountWorkflowInvocationShare({ bothShareable: true });
        expect(wrapper.findComponent(GModal).props("show")).toBe(false);

        await clickShareIcon(wrapper);

        expect(wrapper.findComponent(GModal).props("show")).toBe(false);
        expect(raisedToasts()).toEqual([{ variant: "info", message: CLIPBOARD_MSG }]);
        expect(writeText).toHaveBeenCalledExactlyOnceWith(INVOCATION_LINK);
    });
});
