import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

import { generateRandomString } from "./testUtils";

import WorkflowRunButton from "./WorkflowRunButton.vue";

const localVue = getLocalVue();

const WORKFLOW_ID = generateRandomString();
const WORKFLOW_VERSION = 1;
const WORKFLOW_RUN_BUTTON_SELECTOR = `[data-workflow-run="${WORKFLOW_ID}"]`;

async function mountWorkflowRunButton(props?: { id: string; version: number; full?: boolean }) {
    const wrapper = mount(WorkflowRunButton as object, {
        propsData: { ...props },
        localVue,
    });

    return { wrapper };
}

describe("WorkflowRunButton.vue", () => {
    it("should render button with icon and route", async () => {
        const { wrapper } = await mountWorkflowRunButton({ id: WORKFLOW_ID, version: WORKFLOW_VERSION });

        const button = wrapper.find(WORKFLOW_RUN_BUTTON_SELECTOR);
        expect(button.attributes("title")).toBe("Run workflow");
        expect(button.text()).toBe("");
        expect(button.attributes("href")).toBe(`/workflows/run?id=${WORKFLOW_ID}&version=${WORKFLOW_VERSION}`);
    });
});
