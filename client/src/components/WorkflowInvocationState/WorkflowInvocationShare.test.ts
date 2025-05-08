import { createTestingPinia } from "@pinia/testing";
import { getFakeRegisteredUser } from "@tests/test-data";
import { shallowMount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { getLocalVue } from "tests/jest/helpers";

import { useServerMock } from "@/api/client/__mocks__/index";
import { useUserStore } from "@/stores/userStore";

import WorkflowInvocationShare from "./WorkflowInvocationShare.vue";

// Constants
const WORKFLOW_OWNER = "test-user";
const OTHER_USER = "other-user";
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
const SHARED_WORKFLOW_ID = "shared-workflow-id";
const TEST_HISTORY = {
    id: "test-history-id",
    name: "test-history-name",
    archived: false,
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

const SELECTORS = {
    SHARE_ICON_BUTTON: "[data-description='share invocation icon button']",
    MODAL: "[data-description='share invocation modal']",
};

// Mock the toast composable to track the messages
const MSG = 0;
const TYPE = 1;
const toastMock = jest.fn((message, type: "success" | "info") => {
    return { message, type };
});
jest.mock("@/composables/toast", () => ({
    Toast: {
        success: jest.fn().mockImplementation((message) => {
            toastMock(message, "success");
        }),
        info: jest.fn().mockImplementation((message) => {
            toastMock(message, "info");
        }),
    },
}));

// Mock "@/utils/clipboard"
const writeText = jest.fn();
Object.assign(navigator, {
    clipboard: {
        writeText,
    },
});

// Mock the workflow store to return the sample workflow
jest.mock("@/stores/workflowStore", () => {
    const originalModule = jest.requireActual("@/stores/workflowStore");
    return {
        ...originalModule,
        useWorkflowStore: () => ({
            ...originalModule.useWorkflowStore(),
            getStoredWorkflowByInstanceId: jest.fn().mockImplementation((workflowId: string) => {
                return {
                    ...TEST_WORKFLOW,
                    id: workflowId === SHARED_WORKFLOW_ID ? SHARED_WORKFLOW_ID : TEST_WORKFLOW.id,
                    importable: workflowId === SHARED_WORKFLOW_ID,
                };
            }),
        }),
    };
});

const { server, http } = useServerMock();

const localVue = getLocalVue();

/**
 * Mounts the WorkflowInvocationShare component with props/stores adjusted given the parameters
 * @param ownsWorkflow Whether the user owns the workflow associated with the invocation
 * @param bothShareable Whether the workflow and history are already shareable
 * @returns The wrapper object
 */
async function mountWorkflowInvocationShare(ownsWorkflow = true, bothShareable = false) {
    server.use(
        http.get("/api/histories/{history_id}", ({ response }) => {
            return response(200).json({
                ...TEST_HISTORY,
                importable: bothShareable,
            });
        }),

        http.put("/api/workflows/{workflow_id}/enable_link_access", ({ response }) => {
            return response(200).json({
                ...TEST_WORKFLOW,
                importable: true,
            });
        }),

        http.put("/api/histories/{history_id}/enable_link_access", ({ response }) => {
            return response(200).json(TEST_HISTORY_POST_SHARE);
        })
    );

    const wrapper = shallowMount(WorkflowInvocationShare as object, {
        propsData: {
            invocationId: "invocation-id",
            workflowId: bothShareable ? SHARED_WORKFLOW_ID : TEST_WORKFLOW.id,
            historyId: TEST_HISTORY.id,
        },
        localVue,
        pinia: createTestingPinia(),
    });

    const userStore = useUserStore();
    userStore.currentUser = getFakeRegisteredUser({
        username: ownsWorkflow ? WORKFLOW_OWNER : OTHER_USER,
    });

    await flushPromises();

    return { wrapper };
}

async function openShareModal(wrapper: Wrapper<Vue>) {
    await wrapper.find(SELECTORS.SHARE_ICON_BUTTON).trigger("click");
}

describe("WorkflowInvocationShare", () => {
    beforeEach(() => {
        (navigator.clipboard.writeText as jest.Mock).mockResolvedValue(undefined);
    });

    it("opens the modal with the expected history and workflow information", async () => {
        const { wrapper } = await mountWorkflowInvocationShare();

        // Initially, the modal is not visible and opens when the button is clicked
        expect(wrapper.find(SELECTORS.MODAL).attributes("visible")).toBeUndefined();
        await openShareModal(wrapper);
        expect(wrapper.find(SELECTORS.MODAL).attributes("visible")).toBe("true");

        expect(wrapper.find(SELECTORS.MODAL).text()).toContain(TEST_WORKFLOW.name);
        expect(wrapper.find(SELECTORS.MODAL).text()).toContain(TEST_HISTORY.name);
    });

    it("shares the workflow and history when the share button is clicked, and copies link", async () => {
        const { wrapper } = await mountWorkflowInvocationShare();

        await openShareModal(wrapper);

        // Click the share button in the modal
        wrapper.find(SELECTORS.MODAL).vm.$emit("ok");
        await flushPromises();

        // We have 2 toasts
        const toasts = toastMock.mock.calls;
        expect(toasts.length).toBe(2);

        // The first one is the success message for sharing the workflow and history
        expect(toasts[0]![MSG]).toBe(SHARE_SUCCESS_MSG);
        expect(toasts[0]![TYPE]).toBe("success");

        // The second one is the copied link message
        expect(toasts[1]![MSG]).toBe(CLIPBOARD_MSG);
        expect(toasts[1]![TYPE]).toBe("info");
    });

    it("renders nothing when the user does not own the workflow", async () => {
        const { wrapper } = await mountWorkflowInvocationShare(false);
        expect(wrapper.find(SELECTORS.SHARE_ICON_BUTTON).exists()).toBe(false);
        expect(wrapper.find(SELECTORS.MODAL).exists()).toBe(false);
    });

    it("just copies link and does not open modal if both workflow and history are already shareable", async () => {
        const { wrapper } = await mountWorkflowInvocationShare(true, true);

        // Initially, the modal is not visible and this time remains closed when the button is clicked
        expect(wrapper.find(SELECTORS.MODAL).attributes("visible")).toBeUndefined();
        await openShareModal(wrapper);
        expect(wrapper.find(SELECTORS.MODAL).attributes("visible")).toBeUndefined();

        // Instead we already have a singular toast with the link copied message
        const toasts = toastMock.mock.calls;
        expect(toasts.length).toBe(1);
        expect(toasts[0]![MSG]).toBe(CLIPBOARD_MSG);
        expect(toasts[0]![TYPE]).toBe("info");
    });
});
