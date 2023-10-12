import { mount } from "@vue/test-utils";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import flushPromises from "flush-promises";
import { getLocalVue } from "tests/jest/helpers";

import MountTarget from "./FormLibraryData.vue";

const localVue = getLocalVue();

function createTarget(propsData) {
    const axiosMock = new MockAdapter(axios);
    const libraryList = [{ id: "library_0", name: "library_name_0" }];
    const datasetList = [
        { id: "not_ldda", name: "not_ldda", type: "other" },
        { id: "ldda_0", name: "ldda_0", type: "file" },
        { id: "ldda_1", name: "ldda_1", type: "file" },
    ];
    axiosMock.onGet("/api/libraries?deleted=false").reply(200, libraryList);
    axiosMock.onGet("api/libraries/library_0/contents").reply(200, datasetList);
    return mount(MountTarget, {
        propsData,
        localVue,
    });
}

describe("FormLibraryData", () => {
    it("displays select fields", async () => {
        const wrapper = createTarget({ id: "data_library_field" });
        expect(wrapper.find(".alert-warning").text()).toBe("No options available.");
        expect(wrapper.find(".text-muted").text()).toBe("The selected library does not contain any datasets.");
        await flushPromises();
        const options = wrapper.findAll(".multiselect__option");
        expect(options.at(0).text()).toBe("library_name_0");
        expect(options.at(3).text()).toBe("ldda_0");
        expect(options.at(4).text()).toBe("ldda_1");
        const addButton = wrapper.find("[data-description='form library add dataset']");
        await addButton.trigger("click");
        const newValue = wrapper.emitted().input[0][0];
        expect(newValue).toEqual([{ id: "ldda_0", name: "ldda_0" }]);
        await wrapper.setProps({ value: newValue });
        const removeButton = wrapper.find("[data-description='form library remove dataset']");
        await removeButton.trigger("click");
        const emptyValue = wrapper.emitted().input[1][0];
        expect(emptyValue).toBe(null);
    });
});
