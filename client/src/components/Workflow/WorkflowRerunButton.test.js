import WorkflowRerunButton from "./WorkflowRerunButton";
import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import { ROOT_COMPONENT } from "utils/navigation";

import "jest-location-mock";

const localVue = getLocalVue(true);
const WORKFLOW_ID = "workflow_id123";
const INVOCATION_ID = "invocation_id456";

describe("WorkflowRerunButton.vue", () => {
    let wrapper;

    beforeEach(async () => {
        const propsData = {
            root: "/root/",
            workflowId: WORKFLOW_ID,
            invocationId: INVOCATION_ID,
        };
        wrapper = shallowMount(WorkflowRerunButton, {
            propsData,
            localVue,
        });
    });

    it("should localize title text", async () => {
        const selector = ROOT_COMPONENT.workflows.run_button({
            workflowId: WORKFLOW_ID,
            invocationId: INVOCATION_ID,
        }).selector;
        expect(wrapper.find(selector).attributes("title")).toBeLocalizationOf("Rerun invocation");
    });
});
