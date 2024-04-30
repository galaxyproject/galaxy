import { createTestingPinia } from "@pinia/testing";
import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

import invocationData from "../Workflow/test/json/invocation.json";
import WorkflowInvocationOverview from "./WorkflowInvocationOverview";

const localVue = getLocalVue();

describe("WorkflowInvocationOverview.vue with terminal invocation", () => {
    let wrapper;
    let propsData;

    beforeEach(async () => {
        propsData = {
            invocation: invocationData,
            invocationAndJobTerminal: true,
            invocationSchedulingTerminal: true,
            jobStatesSummary: {},
        };
        wrapper = shallowMount(WorkflowInvocationOverview, {
            propsData,
            localVue,
            pinia: createTestingPinia(),
        });
    });

    it("displays pdf report links", async () => {
        expect(wrapper.find(".invocation-pdf-link").exists()).toBeTruthy();
    });

    it("doesn't show cancel invocation button", async () => {
        expect(wrapper.find(".cancel-workflow-scheduling").exists()).toBeFalsy();
    });
});

describe("WorkflowInvocationOverview.vue with invocation scheduling running", () => {
    let wrapper;
    let propsData;
    let store;

    beforeEach(async () => {
        propsData = {
            invocation: invocationData,
            invocationAndJobTerminal: false,
            invocationSchedulingTerminal: false,
            jobStatesSummary: {},
        };
        wrapper = shallowMount(WorkflowInvocationOverview, {
            store,
            propsData,
            localVue,
        });
    });

    it("does not display pdf report links", async () => {
        expect(wrapper.find(".invocation-pdf-link").exists()).toBeFalsy();
    });

    it("shows cancel invocation button", async () => {
        expect(wrapper.find(".cancel-workflow-scheduling").exists()).toBeTruthy();
    });
});
