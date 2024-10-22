import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

import { generateRandomString } from "./testUtils";

import WorkflowRunButton from "./WorkflowRunButton.vue";

const localVue = getLocalVue();

const WORKFLOW_ID = generateRandomString();
const WORKFLOW_RUN_BUTTON_SELECTOR = `[data-workflow-run="${WORKFLOW_ID}"]`;

async function mountWorkflowRunButton(props?: { id: string; full?: boolean }) {
    const wrapper = mount(WorkflowRunButton as object, {
        propsData: { ...props },
        localVue,
    });

    return { wrapper };
}

describe("WorkflowRunButton.vue", () => {
    it("should render button with icon", async () => {
        const { wrapper } = await mountWorkflowRunButton({ id: WORKFLOW_ID });

        expect(wrapper.find(WORKFLOW_RUN_BUTTON_SELECTOR).exists()).toBeTruthy();
        expect(wrapper.find(WORKFLOW_RUN_BUTTON_SELECTOR).attributes("title")).toBe("Run workflow");
        expect(wrapper.find(WORKFLOW_RUN_BUTTON_SELECTOR).text()).toBe("");
    });

    it("should redirect to workflow run page", async () => {
        const { wrapper } = await mountWorkflowRunButton({ id: WORKFLOW_ID });

        const runButton = await wrapper.find(WORKFLOW_RUN_BUTTON_SELECTOR);

        expect(runButton.attributes("href")).toBe(`/workflows/run?id=${WORKFLOW_ID}`);
    });
});
