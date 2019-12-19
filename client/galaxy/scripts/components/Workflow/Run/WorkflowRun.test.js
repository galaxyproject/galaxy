import MockAdapter from "axios-mock-adapter";
import axios from "axios";
import { __RewireAPI__ as rewire } from "./WorkflowRun";
import WorkflowRun from "./WorkflowRun.vue";
import { mount, createLocalVue } from "@vue/test-utils";

import sampleRunData1 from "./testdata/run1.json";

const run1WorkflowId = "ebab00128497f9d7";

describe("WorkflowRun.vue", () => {
    let axiosMock;
    let wrapper;
    let localVue;

    beforeEach(() => {
        axiosMock = new MockAdapter(axios);
        rewire.__Rewire__("getAppRoot", () => "/");

        const propsData = { workflowId: run1WorkflowId };
        localVue = createLocalVue();
        axiosMock.onGet(`/api/workflows/${run1WorkflowId}/download?style=run`).reply(200, sampleRunData1);
        wrapper = mount(WorkflowRun, {
            propsData: propsData,
            localVue
        });
    });

    afterEach(() => {
        axiosMock.restore();
    });

    it("loads run data from API and parses it into a WorkflowRunModel object", async () => {
        expect(wrapper.vm.loading).to.equal(true);
        expect(wrapper.vm.error).to.equal(null);
        expect(wrapper.vm.model).to.equal(null);
        await localVue.nextTick();
        await localVue.nextTick();
        await localVue.nextTick();
        await localVue.nextTick();
        expect(wrapper.vm.error).to.equal(null);
        expect(wrapper.vm.loading).to.equal(false);
        const model = wrapper.vm.model;
        expect(model).to.not.equal(null);
        expect(model.workflowId).to.equal(run1WorkflowId);
        expect(model.name).to.equal("Cool Test Workflow");
        expect(model.historyId).to.equal("8f7a155755f10e73");
        expect(model.hasUpgradeMessages).to.equal(false);
        expect(model.hasStepVersionChanges).to.equal(false);
        expect(model.wpInputs.wf_param.label).to.equal("wf_param");
    });
});
