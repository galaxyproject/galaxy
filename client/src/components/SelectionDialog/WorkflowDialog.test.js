import MockAdapter from "axios-mock-adapter";
import axios from "axios";
import WorkflowDialog from "./WorkflowDialog.vue";
import { __RewireAPI__ as rewire } from "components/Workflow/services";
import SelectionDialog from "./SelectionDialog.vue";
import { setupTestGalaxy } from "qunit/test-app";

import { shallowMount, createLocalVue } from "@vue/test-utils";

const mockOptions = {
    callback: () => {},
    modalStatic: true,
};

describe("WorkflowDialog.vue", () => {
    let wrapper;
    let localVue;
    let axiosMock;

    beforeEach(() => {
        axiosMock = new MockAdapter(axios);
        setupTestGalaxy();
        rewire.__Rewire__("_addAttributes", (workflow) => workflow);
        localVue = createLocalVue();
        wrapper = shallowMount(WorkflowDialog, {
            propsData: mockOptions,
            localVue: localVue,
        });
    });

    afterEach(() => {
        axiosMock.restore();
    });

    it("loads correctly in loading state, shows options when optionsShow becomes true", async () => {
        // Initially in loading state.
        const workflowsResponse = [{ id: "f2db41e1fa331b3e", name: "Awesome Workflow" }];
        axiosMock.onGet("/api/workflows").reply(200, workflowsResponse);

        expect(wrapper.find(SelectionDialog).is(SelectionDialog)).to.equals(true);
        expect(wrapper.vm.optionsShow).to.equals(false);

        await localVue.nextTick();
        await localVue.nextTick();
        await localVue.nextTick();

        // why not shown?
        expect(wrapper.vm.errorMessage).to.equals(null);
        expect(wrapper.vm.optionsShow).to.equals(true);
    });

    it("error message set on workflow fetch problems", async () => {
        expect(wrapper.vm.errorMessage).to.equals(null);
        axiosMock.onGet("/api/workflows").reply(403, { err_msg: "Bad error" });
        await localVue.nextTick();
        await localVue.nextTick();
        await localVue.nextTick();
        await localVue.nextTick();
        expect(wrapper.vm.errorMessage).to.equals("Bad error");
    });
});
