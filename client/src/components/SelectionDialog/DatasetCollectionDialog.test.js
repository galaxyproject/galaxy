import { mount } from "@vue/test-utils";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import { BAlert, BTable } from "bootstrap-vue";
import flushPromises from "flush-promises";
import { getLocalVue } from "tests/jest/helpers";

import DatasetCollectionDialog from "./DatasetCollectionDialog.vue";
import SelectionDialog from "./SelectionDialog.vue";

jest.mock("app");

const globalConfig = getLocalVue();

const mockOptions = {
    callback: () => {},
    modalStatic: true,
    history: "f2db41e1fa331b3e",
};

describe("DatasetCollectionDialog.vue", () => {
    let wrapper;
    let axiosMock;

    beforeEach(() => {
        axiosMock = new MockAdapter(axios);
    });

    afterEach(() => {
        axiosMock.restore();
    });

    it("loads correctly in loading state, shows options when optionsShow becomes true", async () => {
        // Initially in loading state.
        const collectionsResponse = [{ id: "f2db41e1fa331b3e", name: "Awesome Collection", hid: 1 }];
        axiosMock
            .onGet(`/api/histories/${mockOptions.history}/contents?type=dataset_collection`)
            .reply(200, collectionsResponse);

        wrapper = mount(DatasetCollectionDialog, {
            props: mockOptions,
            global: globalConfig.global,
        });

        expect(wrapper.findComponent(SelectionDialog).exists()).toBe(true);
        expect(wrapper.findComponent(BTable).exists()).toBe(false);

        await flushPromises();

        expect(wrapper.findComponent(BAlert).exists()).toBe(false);
        expect(wrapper.findComponent(BTable).exists()).toBe(true);
    });

    it("error message set on dataset collection fetch problems", async () => {
        expect(wrapper.findComponent(BAlert).exists()).toBe(false);
        axiosMock
            .onGet(`/api/histories/${mockOptions.history}/contents?type=dataset_collection`)
            .reply(403, { err_msg: "Bad error" });
        wrapper = mount(DatasetCollectionDialog, {
            props: mockOptions,
            global: globalConfig.global,
        });
        await flushPromises();
        expect(wrapper.findComponent(BAlert).text()).toBe("Bad error");
    });
});
