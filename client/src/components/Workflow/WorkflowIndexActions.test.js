import WorkflowIndexActions from "./WorkflowIndexActions";
import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import { ROOT_COMPONENT } from "utils/navigation";
import VueRouter from "vue-router";
import { PiniaVuePlugin } from "pinia";
import { createTestingPinia } from "@pinia/testing";

import "jest-location-mock";

const localVue = getLocalVue(true);
localVue.use(VueRouter);
localVue.use(PiniaVuePlugin);

const router = new VueRouter();

function getCurrentPath($router) {
    return $router.history.current.path;
}

describe("WorkflowIndexActions", () => {
    let wrapper;
    let $router;

    beforeEach(async () => {
        wrapper = shallowMount(WorkflowIndexActions, {
            localVue,
            router,
            pinia: createTestingPinia(),
        });
        $router = wrapper.vm.$router;
    });

    describe("naviation", () => {
        it("should create a workflow when create is clicked", async () => {
            await wrapper.find(ROOT_COMPONENT.workflows.new_button.selector).trigger("click");
            expect(getCurrentPath($router)).toBe("/workflows/create");
        });

        it("should import a workflow when create is clicked", async () => {
            await wrapper.find(ROOT_COMPONENT.workflows.import_button.selector).trigger("click");
            expect(getCurrentPath($router)).toBe("/workflows/import");
        });

        it("should localize button text", async () => {
            expect(wrapper.find(ROOT_COMPONENT.workflows.new_button.selector).text()).toBeLocalizationOf("Create");
            expect(wrapper.find(ROOT_COMPONENT.workflows.import_button.selector).text()).toBeLocalizationOf("Import");
        });
    });
});
