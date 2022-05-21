import WorkflowIndexActions from "./WorkflowIndexActions";
import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";

import "jest-location-mock";

const localVue = getLocalVue();

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
            await wrapper.find("#workflow-create").trigger("click");
            expect(window.location).toBeAt("/root/workflows/create");
        });

        it("should import a workflow when create is clicked", async () => {
            await wrapper.find("#workflow-import").trigger("click");
            expect(window.location).toBeAt("/root/workflows/import");
        });
    });
});
