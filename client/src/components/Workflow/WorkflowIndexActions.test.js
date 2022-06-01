import WorkflowIndexActions from "./WorkflowIndexActions";
import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import { ROOT_COMPONENT } from "utils/navigation";

import "jest-location-mock";

const localVue = getLocalVue(true);

describe("WorkflowIndexActions.vue", () => {
    let wrapper;

    beforeEach(async () => {
        const propsData = {
            root: "/root/",
        };
        wrapper = shallowMount(WorkflowIndexActions, {
            propsData,
            localVue,
        });
    });

    describe("naviation", () => {
        it("should create a workflow when create is clicked", async () => {
            await wrapper.find(ROOT_COMPONENT.workflows.new_button.selector).trigger("click");
            expect(window.location).toBeAt("/root/workflows/create");
        });

        it("should import a workflow when create is clicked", async () => {
            await wrapper.find(ROOT_COMPONENT.workflows.import_button.selector).trigger("click");
            expect(window.location).toBeAt("/root/workflows/import");
        });

        it("should localize button text", async () => {
            expect(wrapper.find(ROOT_COMPONENT.workflows.new_button.selector).text()).toBeLocalizationOf("Create");
            expect(wrapper.find(ROOT_COMPONENT.workflows.import_button.selector).text()).toBeLocalizationOf("Import");
        });
    });
});
