import { createTestingPinia } from "@pinia/testing";
import { getFakeRegisteredUser } from "@tests/test-data";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { getLocalVue } from "tests/jest/helpers";

import { useServerMock } from "@/api/client/__mocks__";
import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";

import WorkflowAnnotation from "./WorkflowAnnotation.vue";

// Constants
const WORKFLOW_OWNER = "test-user";
const OTHER_USER = "other-user";
const WORKFLOW_UPDATE_TIME = "2023-01-01T00:00:00.000Z";
const INVOCATION_TIME = "2024-01-01T00:00:00.000Z";
const SAMPLE_WORKFLOW = {
    id: "workflow-id",
    name: "workflow-name",
    owner: WORKFLOW_OWNER,
    version: 1,
    update_time: WORKFLOW_UPDATE_TIME,
};
const OTHER_USER_WORKFLOW_ID = "other-user-workflow-id";
const SAMPLE_RUN_COUNT = 100;
const TEST_HISTORY_ID = "test-history-id";
const TEST_HISTORY = {
    id: TEST_HISTORY_ID,
    name: "fake-history-name",
};

const SELECTORS = {
    RUN_COUNT: ".workflow-invocations-count",
    INDICATORS_LINK: '[data-description="published owner badge"]',
    SWITCH_TO_HISTORY_LINK: "[data-description='switch to history link']",
    TIME_INFO: '[data-description="workflow annotation time info"]',
    DATE: '[data-description="workflow annotation date"]',
};

// Mock the workflow store to return the sample workflow
jest.mock("@/stores/workflowStore", () => {
    const originalModule = jest.requireActual("@/stores/workflowStore");
    return {
        ...originalModule,
        useWorkflowStore: () => ({
            ...originalModule.useWorkflowStore(),
            getStoredWorkflowByInstanceId: jest.fn().mockImplementation((id: string) => {
                if (id === OTHER_USER_WORKFLOW_ID) {
                    return { ...SAMPLE_WORKFLOW, id: OTHER_USER_WORKFLOW_ID, published: true };
                }
                return SAMPLE_WORKFLOW;
            }),
        }),
    };
});

jest.mock("@/stores/historyStore"),
    () => {
        const originalModule = jest.requireActual("@/stores/historyStore");
        return {
            ...originalModule,
            useHistoryStore: () => ({
                ...originalModule.useHistoryStore(),
                getHistoryById: jest.fn().mockImplementation(() => TEST_HISTORY),
            }),
        };
    };

const localVue = getLocalVue();
const { server, http } = useServerMock();

/**
 * Mounts the WorkflowAnnotation component with props/stores adjusted given the parameters
 * @param version The version of the component to mount (`run_form` or `invocation` view)
 * @param ownsWorkflow Whether the user owns the workflow
 * @returns The wrapper object
 */
async function mountWorkflowAnnotation(version: "run_form" | "invocation", ownsWorkflow = true) {
    server.use(
        http.get("/api/histories/{history_id}", ({ response }) => {
            return response(200).json(TEST_HISTORY);
        })
    );
    server.use(
        http.get("/api/workflows/{workflow_id}/counts", ({ response }) => {
            return response(200).json({ scheduled: SAMPLE_RUN_COUNT });
        })
    );

    const wrapper = mount(WorkflowAnnotation as object, {
        propsData: {
            workflowId: ownsWorkflow ? SAMPLE_WORKFLOW.id : OTHER_USER_WORKFLOW_ID,
            historyId: TEST_HISTORY_ID,
            invocationUpdateTime: version === "invocation" ? INVOCATION_TIME : undefined,
            showDetails: version === "run_form",
        },
        localVue,
        pinia: createTestingPinia(),
        stubs: {
            FontAwesomeIcon: true,
        },
    });

    const historyStore = useHistoryStore();
    historyStore.setCurrentHistoryId(TEST_HISTORY_ID);

    const userStore = useUserStore();
    userStore.currentUser = getFakeRegisteredUser({
        username: ownsWorkflow ? WORKFLOW_OWNER : OTHER_USER,
    });

    await flushPromises();

    return { wrapper };
}

describe("WorkflowAnnotation renders", () => {
    it("the run count and history, not indicators if owned not published", async () => {
        async function checkHasRunCount(version: "run_form" | "invocation") {
            const { wrapper } = await mountWorkflowAnnotation(version);

            const runCount = wrapper.find(SELECTORS.RUN_COUNT);
            expect(runCount.text()).toContain("workflow runs:");
            expect(runCount.text()).toContain(SAMPLE_RUN_COUNT.toString());

            if (version === "run_form") {
                expect(wrapper.find(SELECTORS.SWITCH_TO_HISTORY_LINK).exists()).toBe(false);
            } else {
                expect(wrapper.find(SELECTORS.SWITCH_TO_HISTORY_LINK).text()).toBe(TEST_HISTORY.name);
            }

            // Since this is the user's own workflow, the indicators link
            // (to view all published workflows by the owner) should not be present
            expect(wrapper.find(SELECTORS.INDICATORS_LINK).exists()).toBe(false);
        }
        await checkHasRunCount("run_form");
        await checkHasRunCount("invocation");
    });

    it("workflow indicators if the user does not own the workflow", async () => {
        // we assume it is another user's published workflow in this case

        async function checkHasIndicators(version: "run_form" | "invocation") {
            const { wrapper } = await mountWorkflowAnnotation(version, false);

            const indicatorsLink = wrapper.find(SELECTORS.INDICATORS_LINK);
            expect(indicatorsLink.text()).toBe(WORKFLOW_OWNER);
            expect(indicatorsLink.attributes("title")).toContain(
                `Click to view all published workflows by '${WORKFLOW_OWNER}'`
            );
        }
        await checkHasIndicators("run_form");
        await checkHasIndicators("invocation");
    });

    it("renders time since edit if run form view", async () => {
        const { wrapper } = await mountWorkflowAnnotation("run_form");

        const timeInfo = wrapper.find(SELECTORS.TIME_INFO);
        expect(timeInfo.text()).toContain("edited");
        expect(timeInfo.find(SELECTORS.DATE).attributes("title")).toBe(WORKFLOW_UPDATE_TIME);
    });

    it("renders time since invocation if invocation view", async () => {
        const { wrapper } = await mountWorkflowAnnotation("invocation");

        const timeInfo = wrapper.find(SELECTORS.TIME_INFO);
        expect(timeInfo.text()).toContain("invoked");
        expect(timeInfo.find(SELECTORS.DATE).attributes("title")).toBe(INVOCATION_TIME);
    });
});
