import { createTestingPinia } from "@pinia/testing";
import { getFakeRegisteredUser } from "@tests/test-data";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { getLocalVue } from "tests/jest/helpers";

import sampleInvocation from "@/components/Workflow/test/json/invocation.json";
import { useUserStore } from "@/stores/userStore";

import WorkflowNavigationTitle from "./WorkflowNavigationTitle.vue";

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
    WORKFLOW_HEADING: "[data-description='workflow heading']",
    ACTIONS_BUTTON_GROUP: "bbuttongroup-stub",
    EDIT_WORKFLOW_BUTTON: `bbutton-stub[title='<b>Edit</b><br>${SAMPLE_WORKFLOW.name}']`,
    IMPORT_WORKFLOW_BUTTON: "[data-description='import workflow button']",
    EXECUTE_WORKFLOW_BUTTON: "[data-description='execute workflow button']",
    ROUTE_TO_RUN_BUTTON: "[data-description='route to workflow run button']",
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
 * Mounts the WorkflowNavigationTitle component with props/stores adjusted given the parameters
 * @param version The version of the component to mount (`run_form` or `invocation` view)
 * @param ownsWorkflow Whether the user owns the workflow associated with the invocation
 * @param unimportableWorkflow Whether the workflow import should fail
 * @returns The wrapper object, and the mockRouter object
 */
async function mountWorkflowNavigationTitle(
    version: "run_form" | "invocation",
    ownsWorkflow = true,
    unimportableWorkflow = false
) {
    const mockRouter = {
        push: jest.fn(),
    };

    let workflowId: string;
    let invocation;
    if (version === "invocation") {
        workflowId = !unimportableWorkflow ? sampleInvocation.workflow_id : UNIMPORTABLE_WORKFLOW_INSTANCE_ID;
        invocation = {
            ...sampleInvocation,
            workflow_id: workflowId,
        };
    } else {
        workflowId = !unimportableWorkflow ? SAMPLE_WORKFLOW.id : UNIMPORTABLE_WORKFLOW_INSTANCE_ID;
        invocation = undefined;
    }

    const wrapper = shallowMount(WorkflowNavigationTitle as object, {
        propsData: {
            invocation,
            workflowId,
        },
        localVue,
        mocks: {
            $router: mockRouter,
        },
        pinia: createTestingPinia(),
    });

    const userStore = useUserStore();
    userStore.currentUser = getFakeRegisteredUser({
        username: ownsWorkflow ? WORKFLOW_OWNER : OTHER_USER,
    });

    return { wrapper, mockRouter };
}

describe("WorkflowNavigationTitle renders", () => {
    it("the workflow name in header and run button in actions; invocation version", async () => {
        const { wrapper } = await mountWorkflowNavigationTitle("invocation");

        const heading = wrapper.find(SELECTORS.WORKFLOW_HEADING);
        expect(heading.text()).toContain(`Invoked Workflow: ${SAMPLE_WORKFLOW.name}`);
        expect(heading.text()).toContain(`(version: ${SAMPLE_WORKFLOW.version + 1})`);

        const actionsGroup = wrapper.find(SELECTORS.ACTIONS_BUTTON_GROUP);
        const runButton = actionsGroup.find(SELECTORS.ROUTE_TO_RUN_BUTTON);
        expect(runButton.attributes("title")).toContain("Rerun");
        expect(runButton.attributes("title")).toContain(SAMPLE_WORKFLOW.name);
    });

    it("the workflow name in header and run button in actions; run form version", async () => {
        const { wrapper } = await mountWorkflowNavigationTitle("run_form");

        const heading = wrapper.find(SELECTORS.WORKFLOW_HEADING);
        expect(heading.text()).toContain(`Workflow: ${SAMPLE_WORKFLOW.name}`);
        expect(heading.text()).toContain(`(version: ${SAMPLE_WORKFLOW.version + 1})`);

        const actionsGroup = wrapper.find(SELECTORS.ACTIONS_BUTTON_GROUP);
        const runButton = actionsGroup.find(SELECTORS.EXECUTE_WORKFLOW_BUTTON);
        expect(runButton.attributes("title")).toContain("Run");
    });

    it("edit button if user owns the workflow", async () => {
        async function findAndClickEditButton(version: "invocation" | "run_form") {
            const { wrapper, mockRouter } = await mountWorkflowNavigationTitle(version);
            const actionsGroup = wrapper.find(SELECTORS.ACTIONS_BUTTON_GROUP);

            const editButton = actionsGroup.find(SELECTORS.EDIT_WORKFLOW_BUTTON);
            await editButton.trigger("click");
            await flushPromises();

            expect(mockRouter.push).toHaveBeenCalledTimes(1);
            expect(mockRouter.push).toHaveBeenCalledWith(
                `/workflows/edit?id=${SAMPLE_WORKFLOW.id}&version=${SAMPLE_WORKFLOW.version}`
            );
        }
        await findAndClickEditButton("invocation");
        await findAndClickEditButton("run_form");
    });

    it("import button instead if user does not own the workflow", async () => {
        async function findImportButton(version: "invocation" | "run_form") {
            const { wrapper } = await mountWorkflowNavigationTitle(version, false);
            const actionsGroup = wrapper.find(SELECTORS.ACTIONS_BUTTON_GROUP);
            const importButton = actionsGroup.find(SELECTORS.IMPORT_WORKFLOW_BUTTON);
            expect(importButton.exists()).toBe(true);
        }
        await findImportButton("invocation");
        await findImportButton("run_form");
    });
});

describe("Importing a workflow in WorkflowNavigationTitle", () => {
    // We only need to test the `invocation` version because the button is the same in both versions

    it("should show a confirmation dialog when the import is successful", async () => {
        const { wrapper } = await mountWorkflowNavigationTitle("invocation", false);
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
        const { wrapper } = await mountWorkflowNavigationTitle("invocation", false, true);
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
