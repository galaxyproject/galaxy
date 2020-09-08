import MockAdapter from "axios-mock-adapter";
import axios from "axios";
import DatasetCollectionDialog from "./DatasetCollectionDialog.vue";
import SelectionDialog from "./SelectionDialog.vue";
import flushPromises from "flush-promises";

import { shallowMount, createLocalVue } from "@vue/test-utils";

jest.mock("app");

const mockOptions = {
    callback: () => {},
    modalStatic: true,
    history: "f2db41e1fa331b3e",
};

describe("DatasetCollectionDialog.vue", () => {
    let wrapper;
    let localVue;
    let axiosMock;

    beforeEach(() => {
        axiosMock = new MockAdapter(axios);
        localVue = createLocalVue();
    });

    afterEach(() => {
        axiosMock.restore();
    });

    it("loads correctly in loading state, shows options when optionsShow becomes true", async () => {
        // Initially in loading state.
        const collectionsResponse = [{ id: "f2db41e1fa331b3e", name: "Awesome Collection" }];
        axiosMock
            .onGet(`/api/histories/${mockOptions.history}/contents?type=dataset_collection`)
            .reply(200, collectionsResponse);

        wrapper = shallowMount(DatasetCollectionDialog, {
            propsData: mockOptions,
            localVue: localVue,
        });

        expect(wrapper.findComponent(SelectionDialog).exists()).toBe(true);
        expect(wrapper.vm.optionsShow).toBe(false);

        await flushPromises();

        // why not shown?
        expect(wrapper.vm.errorMessage).toBeNull();
        expect(wrapper.vm.optionsShow).toBe(true);
    });

    it("error message set on dataset collection fetch problems", async () => {
        expect(wrapper.vm.errorMessage).toBeNull();
        axiosMock
            .onGet(`/api/histories/${mockOptions.history}/contents?type=dataset_collection`)
            .reply(403, { err_msg: "Bad error" });
        wrapper = shallowMount(DatasetCollectionDialog, {
            propsData: mockOptions,
            localVue: localVue,
        });
        await flushPromises();
        expect(wrapper.vm.errorMessage).toBe("Bad error");
    });
});
