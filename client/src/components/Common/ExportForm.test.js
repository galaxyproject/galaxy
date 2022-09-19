import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
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
});
