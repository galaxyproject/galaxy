import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import ExportForm from "./ExportForm.vue";

const localVue = getLocalVue(true);

jest.mock("components/JobStates/wait");

describe("ExportForm.vue", () => {
    let wrapper;

    beforeEach(async () => {
        wrapper = shallowMount(ExportForm, {
            propsData: {},
            localVue,
        });
    });

    it("should render a form with export disable because inputs empty", async () => {
        expect(wrapper.find(".export-button").exists()).toBeTruthy();
        expect(wrapper.find(".export-button").attributes("disabled")).toBeTruthy();
        expect(wrapper.vm.canExport).toBeFalsy();
    });

    it("should allow export when name and directory available", async () => {
        await wrapper.setData({
            name: "export.tar.gz",
            directory: "gxfiles://",
        });
        expect(wrapper.vm.directory).toEqual("gxfiles://");
        expect(wrapper.vm.name).toEqual("export.tar.gz");
        expect(wrapper.vm.canExport).toBeTruthy();
    });

    it("should localize button text", async () => {
        expect(wrapper.find(".export-button").text()).toBeLocalizationOf("Export");
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

        expect(wrapper.vm.directory).toBe(null);
        expect(wrapper.vm.name).toBe(null);
    });
});
