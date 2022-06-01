import WorkflowRunButton from "./WorkflowRunButton";
import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import { ROOT_COMPONENT } from "utils/navigation";

import "jest-location-mock";

const localVue = getLocalVue(true);
const WORKFLOW_ID = "workflow_id123";

describe("WorkflowRunButton.vue", () => {
    let wrapper;

    beforeEach(async () => {
        const propsData = {
            root: "/root/",
            id: WORKFLOW_ID,
        };
        wrapper = shallowMount(WorkflowRunButton, {
            propsData,
            localVue,
        });
    });

    it("should localize title text", async () => {
        const selector = ROOT_COMPONENT.workflows.run_button({ id: WORKFLOW_ID }).selector;
        expect(wrapper.find(selector).attributes("title")).toBeLocalizationOf("Run workflow");
    });
});
