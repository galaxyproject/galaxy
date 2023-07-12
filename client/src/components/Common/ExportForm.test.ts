import { getLocalVue } from "@tests/jest/helpers";
import { shallowMount } from "@vue/test-utils";

import ExportForm from "./ExportForm.vue";

const localVue = getLocalVue(true);

describe("ExportForm.vue", () => {
    let wrapper: any;

    beforeEach(async () => {
        wrapper = shallowMount(ExportForm, {
            propsData: {},
            localVue,
        });
    });

    it("should render a form with export button disabled because inputs are empty", async () => {
        expect(wrapper.vm.directory).toEqual("");
        expect(wrapper.vm.name).toEqual("");

        expectExportButtonDisabled();
    });

    it("should render a form with export button disabled because directory is empty", async () => {
        await wrapper.setData({
            name: "export.tar.gz",
        });

        expectExportButtonDisabled();
    });

    it("should render a form with export button disabled because name is empty", async () => {
        await wrapper.setData({
            directory: "gxfiles://",
        });

        expectExportButtonDisabled();
    });

    it("should allow export when all inputs are defined", async () => {
        await wrapper.setData({
            name: "export.tar.gz",
            directory: "gxfiles://",
        });

        expectExportButtonEnabled();
    });

    it("should localize button text", async () => {
        const newLocal = wrapper.find(".export-button").text();
        expect(newLocal).toBeLocalizationOf("Export");
    });

    it("should emit 'export' event with correct inputs on export button click", async () => {
        await wrapper.setData({
            name: "export.tar.gz",
            directory: "gxfiles://",
        });
        expect(wrapper.emitted()).not.toHaveProperty("export");

        await wrapper.find(".export-button").trigger("click");

        expect(wrapper.emitted()).toHaveProperty("export");
        expect(wrapper.emitted()["export"][0][0]).toBe("gxfiles://");
        expect(wrapper.emitted()["export"][0][1]).toBe("export.tar.gz");
    });

    it("should clear the inputs after export when clearInputAfterExport is enabled", async () => {
        await wrapper.setProps({
            clearInputAfterExport: true,
        });
        await wrapper.setData({
            name: "export.tar.gz",
            directory: "gxfiles://",
        });
        expect(wrapper.vm.directory).toEqual("gxfiles://");
        expect(wrapper.vm.name).toEqual("export.tar.gz");

        await wrapper.find(".export-button").trigger("click");

        expect(wrapper.vm.directory).toBe("");
        expect(wrapper.vm.name).toBe("");
    });

    function expectExportButtonDisabled() {
        expect(wrapper.find(".export-button").exists()).toBeTruthy();
        expect(wrapper.find(".export-button").attributes("disabled")).toBeTruthy();
    }

    function expectExportButtonEnabled() {
        expect(wrapper.find(".export-button").exists()).toBeTruthy();
        expect(wrapper.find(".export-button").attributes("disabled")).toBeFalsy();
    }
});
