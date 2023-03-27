import WorkflowInvocationState from "./WorkflowInvocationState";
import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import Vuex from "vuex";
import invocationData from "../Workflow/test/json/invocation.json";
import { useConfig } from "composables/config";

jest.mock("composables/config");
useConfig.mockReturnValue({
    config: {
        enable_celery_tasks: true,
    },
    isLoaded: true,
});

const invocationJobsSummaryById = {
    id: "d9833097445452b0",
    model: "WorkflowInvocation",
    states: {},
    populated_state: "ok",
};

const localVue = getLocalVue();

describe("WorkflowInvocationState.vue with terminal invocation", () => {
    let wrapper;
    let propsData;

    beforeEach(async () => {
        propsData = {
            invocationId: invocationData.id,
        };
        wrapper = shallowMount(WorkflowInvocationState, {
            propsData,
            computed: {
                invocation: () => invocationData,
                getInvocationJobsSummaryById: () => () => invocationJobsSummaryById,
            },
            localVue,
        });
    });

    it("determines that invocation and job states are terminal", async () => {
        expect(wrapper.vm.invocationAndJobTerminal).toBeTruthy();
    });
});

describe("WorkflowInvocationState.vue with no invocation", () => {
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
            invocationId: invocationData.id,
        };
        wrapper = shallowMount(WorkflowInvocationState, {
            store,
            propsData,
            computed: {
                invocation: () => null,
                getInvocationJobsSummaryById: () => () => invocationJobsSummaryById,
            },
            localVue,
        });
    });

    it("determines that invocation and job states are not terminal", async () => {
        expect(wrapper.vm.invocationAndJobTerminal).toBeFalsy();
    });
});
