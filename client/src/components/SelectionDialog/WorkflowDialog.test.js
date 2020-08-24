import MockAdapter from "axios-mock-adapter";
import axios from "axios";
import WorkflowDialog from "./WorkflowDialog.vue";
import { __RewireAPI__ as rewire } from "components/Workflow/services";
import SelectionDialog from "./SelectionDialog.vue";
import flushPromises from "flush-promises";

import { shallowMount, createLocalVue } from "@vue/test-utils";

jest.mock("app");

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
        rewire.__Rewire__("_addAttributes", (workflow) => workflow);
        localVue = createLocalVue();
    });

    afterEach(() => {
        axiosMock.restore();
    });

    it("loads correctly in loading state, shows options when optionsShow becomes true", async () => {
        // Initially in loading state.
        axiosMock.onGet("/api/workflows").reply(200, [{ id: "f2db41e1fa331b3e", name: "Awesome Workflow" }]);
        wrapper = shallowMount(WorkflowDialog, {
            propsData: mockOptions,
            localVue: localVue,
        });

        expect(wrapper.findComponent(SelectionDialog));
        expect(wrapper.vm.optionsShow).toBe(false);
        await flushPromises();

        // why not shown?
        expect(wrapper.vm.errorMessage).toBeNull();
        expect(wrapper.vm.optionsShow).toBe(true);
    });

    it("error message set on workflow fetch problems", async () => {
        expect(wrapper.vm.errorMessage).toBeNull();
        axiosMock.onGet("/api/workflows").reply(403, { err_msg: "Bad error" });
        wrapper = shallowMount(WorkflowDialog, {
            propsData: mockOptions,
            localVue: localVue,
        });
        await flushPromises();
        expect(wrapper.vm.errorMessage).toBe("Bad error");
    });
});
