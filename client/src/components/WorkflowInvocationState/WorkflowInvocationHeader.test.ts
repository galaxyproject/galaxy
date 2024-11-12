import { createTestingPinia } from "@pinia/testing";
import { getFakeRegisteredUser } from "@tests/test-data";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { getLocalVue } from "tests/jest/helpers";

import sampleInvocation from "@/components/Workflow/test/json/invocation.json";
import { useUserStore } from "@/stores/userStore";

import WorkflowInvocationHeader from "./WorkflowInvocationHeader.vue";

// Constants
const WORKFLOW_OWNER = "test-user";
const OTHER_USER = "other-user";
const UNIMPORTABLE_WORKFLOW_ID = "invalid-workflow-id";
const UNIMPORTABLE_WORKFLOW_INSTANCE_ID = "invalid-instance-id";
const SAMPLE_WORKFLOW = {
    id: "workflow-id",
    name: "workflow-name",
    owner: WORKFLOW_OWNER,
    version: 1,
};
const IMPORT_ERROR_MESSAGE = "Failed to import workflow";

const SELECTORS = {
    INVOKED_WORKFLOW_HEADING: "anonymous-stub[h1='true']",
    RETURN_TO_INVOCATIONS_LIST_BUTTON: "bbutton-stub[title='Return to Invocations List']",
    ACTIONS_BUTTON_GROUP: "bbuttongroup-stub",
    EDIT_WORKFLOW_BUTTON: `bbutton-stub[title='<b>Edit</b><br>${SAMPLE_WORKFLOW.name}']`,
    IMPORT_WORKFLOW_BUTTON: "anonymous-stub[title='Import this workflow']",
    RUN_WORKFLOW_BUTTON: `anonymous-stub[id='${SAMPLE_WORKFLOW.id}']`,
    ALERT_MESSAGE: "balert-stub",
};

// Mock the copyWorkflow function for importing a workflow
jest.mock("components/Workflow/workflows.services", () => ({
    copyWorkflow: jest.fn().mockImplementation((workflowId: string) => {
        if (workflowId === UNIMPORTABLE_WORKFLOW_ID) {
            throw new Error(IMPORT_ERROR_MESSAGE);
        }
        return SAMPLE_WORKFLOW;
    }),
}));

// Mock the workflow store to return the sample workflow
jest.mock("@/stores/workflowStore", () => {
    const originalModule = jest.requireActual("@/stores/workflowStore");
    return {
        ...originalModule,
        useWorkflowStore: () => ({
            ...originalModule.useWorkflowStore(),
            getStoredWorkflowByInstanceId: jest.fn().mockImplementation((instanceId: string) => {
                if (instanceId === UNIMPORTABLE_WORKFLOW_INSTANCE_ID) {
                    return { ...SAMPLE_WORKFLOW, id: UNIMPORTABLE_WORKFLOW_ID };
                }
                return SAMPLE_WORKFLOW;
            }),
        }),
    };
});

const localVue = getLocalVue();

/**
 * Mounts the WorkflowInvocationHeader component with props/stores adjusted given the parameters
 * @param ownsWorkflow Whether the user owns the workflow associated with the invocation
 * @param hasReturnBtn Whether the component should have a return to invocations list button
 * @param unimportableWorkflow Whether the workflow import should fail
 * @returns The wrapper object
 */
async function mountWorkflowInvocationHeader(ownsWorkflow = true, hasReturnBtn = false, unimportableWorkflow = false) {
    const wrapper = shallowMount(WorkflowInvocationHeader as object, {
        propsData: {
            invocation: {
                ...sampleInvocation,
                workflow_id: !unimportableWorkflow ? sampleInvocation.workflow_id : UNIMPORTABLE_WORKFLOW_INSTANCE_ID,
            },
            invocationState: "scheduled",
            isFullPage: true,
            jobStatesSummary: {},
            fromPanel: !hasReturnBtn,
            invocationSchedulingTerminal: true,
            invocationAndJobTerminal: true,
        },
        localVue,
        pinia: createTestingPinia(),
    });

    const userStore = useUserStore();
    userStore.currentUser = getFakeRegisteredUser({
        username: ownsWorkflow ? WORKFLOW_OWNER : OTHER_USER,
    });

    return { wrapper };
}

describe("WorkflowInvocationHeader renders", () => {
    // Included both cases in one test because these are always constant
    it("(always) the workflow name in header and run button in actions", async () => {
        const { wrapper } = await mountWorkflowInvocationHeader();

        const heading = wrapper.find(SELECTORS.INVOKED_WORKFLOW_HEADING);
        expect(heading.text()).toBe(`Invoked Workflow: "${SAMPLE_WORKFLOW.name}"`);

        const actionsGroup = wrapper.find(SELECTORS.ACTIONS_BUTTON_GROUP);
        const runButton = actionsGroup.find(SELECTORS.RUN_WORKFLOW_BUTTON);
        expect(runButton.attributes("title")).toContain(SAMPLE_WORKFLOW.name);
    });

    it("edit button if user owns the workflow", async () => {
        const { wrapper } = await mountWorkflowInvocationHeader();
        const actionsGroup = wrapper.find(SELECTORS.ACTIONS_BUTTON_GROUP);
        const editButton = actionsGroup.find(SELECTORS.EDIT_WORKFLOW_BUTTON);
        expect(editButton.attributes("to")).toBe(
            `/workflows/edit?id=${SAMPLE_WORKFLOW.id}&version=${SAMPLE_WORKFLOW.version}`
        );
    });

    it("import button instead if user does not own the workflow", async () => {
        const { wrapper } = await mountWorkflowInvocationHeader(false);
        const actionsGroup = wrapper.find(SELECTORS.ACTIONS_BUTTON_GROUP);
        const importButton = actionsGroup.find(SELECTORS.IMPORT_WORKFLOW_BUTTON);
        expect(importButton.exists()).toBe(true);
    });
});

describe("Importing a workflow in WorkflowInvocationHeader", () => {
    it("should show a confirmation dialog when the import is successful", async () => {
        const { wrapper } = await mountWorkflowInvocationHeader(false);
        const actionsGroup = wrapper.find(SELECTORS.ACTIONS_BUTTON_GROUP);
        const importButton = actionsGroup.find(SELECTORS.IMPORT_WORKFLOW_BUTTON);

        // Cannot `.trigger("click")` on `AsyncButton` because it is a stubbed custom component
        await importButton.props().action();
        await flushPromises();

        const alert = wrapper.find(SELECTORS.ALERT_MESSAGE);
        expect(alert.attributes("variant")).toBe("info");
        expect(alert.text()).toContain(`Workflow ${SAMPLE_WORKFLOW.name} imported successfully`);
    });

    it("should show an error dialog when the import fails", async () => {
        const { wrapper } = await mountWorkflowInvocationHeader(false, false, true);
        const actionsGroup = wrapper.find(SELECTORS.ACTIONS_BUTTON_GROUP);
        const importButton = actionsGroup.find(SELECTORS.IMPORT_WORKFLOW_BUTTON);

        // Cannot `.trigger("click")` on `AsyncButton` because it is a stubbed custom component
        await importButton.props().action();
        await flushPromises();

        const alert = wrapper.find(SELECTORS.ALERT_MESSAGE);
        expect(alert.attributes("variant")).toBe("danger");
        expect(alert.text()).toContain(IMPORT_ERROR_MESSAGE);
    });
});
