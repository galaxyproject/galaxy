import WorkflowInvocationSummary from "./WorkflowInvocationSummary";
import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import Vuex from "vuex";
import invocationData from "../Workflow/test/json/invocation.json";

const invocationJobsSummaryById = {
    id: "d9833097445452b0",
    model: "WorkflowInvocation",
    states: {},
    populated_state: "ok",
};

const mockComputed = {
    getInvocationJobsSummaryById: () => () => invocationJobsSummaryById,
};

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
            computed: mockComputed,
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
    let actions;

    beforeEach(async () => {
        actions = {
            fetchInvocationForId: jest.fn(),
            fetchInvocationJobsSummaryForId: jest.fn(),
        };
        store = new Vuex.Store({
            actions,
        });
        propsData = {
            invocation: invocationData,
            invocationAndJobTerminal: false,
            invocationSchedulingTerminal: false,
        };
        wrapper = shallowMount(WorkflowInvocationSummary, {
            store,
            propsData,
            computed: mockComputed,
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
