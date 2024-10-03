import { createTestingPinia } from "@pinia/testing";
import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

import sampleInvocation from "@/components/Workflow/test/json/invocation.json";
import { useUserStore } from "@/stores/userStore";

import WorkflowInvocationHeader from "./WorkflowInvocationHeader.vue";

// Constants
const WORKFLOW_OWNER = "test-user";
const OTHER_USER = "other-user";
const SAMPLE_WORKFLOW = {
    id: "workflow-id",
    name: "workflow-name",
    owner: WORKFLOW_OWNER,
    version: 1,
};
const SELECTORS = {
    INVOKED_WORKFLOW_HEADING: "anonymous-stub[h1='true']",
    RETURN_TO_INVOCATIONS_LIST_BUTTON: "bbutton-stub[title='Return to Invocations List']",
    ACTIONS_BUTTON_GROUP: "bbuttongroup-stub",
    EDIT_WORKFLOW_BUTTON: `bbutton-stub[title='<b>Edit</b><br>${SAMPLE_WORKFLOW.name}']`,
    IMPORT_WORKFLOW_BUTTON: "anonymous-stub[title='Import this workflow']",
    RUN_WORKFLOW_BUTTON: `anonymous-stub[id='${SAMPLE_WORKFLOW.id}']`,
};

// Mock the workflow store to return the expected workflow data given the stored workflow ID
jest.mock("@/stores/workflowStore", () => {
    const originalModule = jest.requireActual("@/stores/workflowStore");
    return {
        ...originalModule,
        useWorkflowStore: () => ({
            ...originalModule.useWorkflowStore(),
            getStoredWorkflowByInstanceId: jest.fn().mockImplementation(() => SAMPLE_WORKFLOW),
            fetchWorkflowForInstanceId: jest.fn().mockImplementation(() => {}),
        }),
    };
});

const localVue = getLocalVue();

async function mountWorkflowRunButton(ownsWorkflow = true, hasReturnBtn = false) {
    const wrapper = shallowMount(WorkflowInvocationHeader as object, {
        propsData: {
            invocation: sampleInvocation,
            fromPanel: !hasReturnBtn,
        },
        localVue,
        pinia: createTestingPinia(),
    });

    const userStore = useUserStore();
    userStore.currentUser = {
        id: "1",
        email: "",
        tags_used: [],
        isAnonymous: false,
        total_disk_usage: 0,
        username: ownsWorkflow ? WORKFLOW_OWNER : OTHER_USER,
    };

    return { wrapper };
}

describe("WorkflowInvocationHeader renders", () => {
    // Included both cases in one test because these are always constant
    it("(always) the workflow name in header and run button in actions", async () => {
        const { wrapper } = await mountWorkflowRunButton();

        const heading = wrapper.find(SELECTORS.INVOKED_WORKFLOW_HEADING);
        expect(heading.text()).toBe(`Invoked Workflow: "${SAMPLE_WORKFLOW.name}"`);

        const actionsGroup = wrapper.find(SELECTORS.ACTIONS_BUTTON_GROUP);
        const runButton = actionsGroup.find(SELECTORS.RUN_WORKFLOW_BUTTON);
        expect(runButton.attributes("title")).toContain(SAMPLE_WORKFLOW.name);
    });

    it("return to invocations list button if not from panel", async () => {
        const { wrapper } = await mountWorkflowRunButton(false, true);
        const returnButton = wrapper.find(SELECTORS.RETURN_TO_INVOCATIONS_LIST_BUTTON);
        expect(returnButton.text()).toBe("Invocations List");
    });

    it("edit button if user owns the workflow", async () => {
        const { wrapper } = await mountWorkflowRunButton();
        const actionsGroup = wrapper.find(SELECTORS.ACTIONS_BUTTON_GROUP);
        const editButton = actionsGroup.find(SELECTORS.EDIT_WORKFLOW_BUTTON);
        expect(editButton.attributes("to")).toBe(
            `/workflows/edit?id=${SAMPLE_WORKFLOW.id}&version=${SAMPLE_WORKFLOW.version}`
        );
    });

    it("import button instead if user does not own the workflow", async () => {
        const { wrapper } = await mountWorkflowRunButton(false);
        const actionsGroup = wrapper.find(SELECTORS.ACTIONS_BUTTON_GROUP);
        const importButton = actionsGroup.find(SELECTORS.IMPORT_WORKFLOW_BUTTON);
        expect(importButton.exists()).toBe(true);
    });
});

// describe("Importing a workflow in WorkflowInvocationHeader", () => {
//     it("should show a confirmation dialog when the import is successful", async () => {
//         const { wrapper } = await mountWorkflowRunButton(false);
//         const actionsGroup = wrapper.find(SELECTORS.ACTIONS_BUTTON_GROUP);
//         const importButton = actionsGroup.find(SELECTORS.IMPORT_WORKFLOW_BUTTON);
//         // await importButton.trigger("click");
//         // await flushPromises();

//         // Clicking doesn't work because the button is an anonymous-stub which has a child button
//         // So we need to call the function the action="[Function]" event which is the attributes("action") of the anonymous-stub
//         const action = importButton.attributes("action");
//         // await (action as any)();
//         // await flushPromises();
//         // logging action just gives [Function], print the actual function
//         if (typeof action === "string") {
//             console.log(action.toString());
//         } else {
//             console.log("Action is not a string");
//         }
//         console.log(wrapper.html());
//     });
// });
