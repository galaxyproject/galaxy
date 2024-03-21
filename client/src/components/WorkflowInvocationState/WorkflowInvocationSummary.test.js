import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

import invocationData from "../Workflow/test/json/invocation.json";
import WorkflowInvocationSummary from "./WorkflowInvocationSummary";

const localVue = getLocalVue();

describe("WorkflowInvocationSummary.vue with terminal invocation", () => {
    let wrapper;
    let propsData;

    beforeEach(async () => {
        propsData = {
            invocation: invocationData,
            invocationAndJobTerminal: true,
            invocationSchedulingTerminal: true,
        };
        wrapper = shallowMount(WorkflowInvocationSummary, {
            propsData,
            localVue,
        });
    });

    it("displays report links", async () => {
        expect(wrapper.find(".invocation-pdf-link").exists()).toBeTruthy();
        expect(wrapper.find(".invocation-report-link").exists()).toBeTruthy();
    });

    it("doesn't show cancel invocation button", async () => {
        expect(wrapper.find(".cancel-workflow-scheduling").exists()).toBeFalsy();
    });
});

describe("WorkflowInvocationSummary.vue with invocation scheduling running", () => {
    let wrapper;
    let propsData;
    let store;

    beforeEach(async () => {
        propsData = {
            invocation: invocationData,
            invocationAndJobTerminal: false,
            invocationSchedulingTerminal: false,
        };
        wrapper = shallowMount(WorkflowInvocationSummary, {
            store,
            propsData,
            localVue,
        });
    });

    it("does not display report links", async () => {
        expect(wrapper.find(".invocation-pdf-link").exists()).toBeFalsy();
        expect(wrapper.find(".invocation-report-link").exists()).toBeFalsy();
    });

    it("shows cancel invocation button", async () => {
        expect(wrapper.find(".cancel-workflow-scheduling").exists()).toBeTruthy();
    });
});
