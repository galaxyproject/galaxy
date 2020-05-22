import MockAdapter from "axios-mock-adapter";
import axios from "axios";
import DatasetCollectionDialog from "./DatasetCollectionDialog.vue";
import { setupTestGalaxy } from "qunit/test-app";
import SelectionDialog from "./SelectionDialog.vue";

import { shallowMount, createLocalVue } from "@vue/test-utils";

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
        setupTestGalaxy();
        localVue = createLocalVue();
        wrapper = shallowMount(DatasetCollectionDialog, {
            propsData: mockOptions,
            localVue: localVue,
        });
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

        expect(wrapper.find(SelectionDialog).is(SelectionDialog)).to.equals(true);
        expect(wrapper.vm.optionsShow).to.equals(false);

        await localVue.nextTick();
        await localVue.nextTick();
        await localVue.nextTick();

        // why not shown?
        expect(wrapper.vm.errorMessage).to.equals(null);
        expect(wrapper.vm.optionsShow).to.equals(true);
    });

    it("error message set on dataset collection fetch problems", async () => {
        expect(wrapper.vm.errorMessage).to.equals(null);
        axiosMock
            .onGet(`/api/histories/${mockOptions.history}/contents?type=dataset_collection`)
            .reply(403, { err_msg: "Bad error" });
        await localVue.nextTick();
        await localVue.nextTick();
        await localVue.nextTick();
        await localVue.nextTick();
        expect(wrapper.vm.errorMessage).to.equals("Bad error");
    });
});
