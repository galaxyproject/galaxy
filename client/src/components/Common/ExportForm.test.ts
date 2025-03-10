import { getLocalVue } from "@tests/jest/helpers";
import { mount } from "@vue/test-utils";

import ExportForm from "./ExportForm.vue";
import FilesInput from "@/components/FilesDialog/FilesInput.vue";

const localVue = getLocalVue(true);

describe("ExportForm.vue", () => {
    let wrapper: any;

    beforeEach(async () => {
        wrapper = mount(ExportForm as object, {
            propsData: {},
            localVue,
        });
    });

    it("should render a form with export button disabled because inputs are empty", async () => {
        expectExportButtonDisabled();
    });

    it("should render a form with export button disabled because directory is empty", async () => {
        const newValue = "export.tar.gz";
        await setNameInput(newValue);

        expectExportButtonDisabled();
    });

    it("should render a form with export button disabled because name is empty", async () => {
        const newValue = "gxfiles://";
        await setDirectoryInput(newValue);

        expectExportButtonDisabled();
    });

    it("should allow export when all inputs are defined", async () => {
        await setNameInput("export.tar.gz");
        await setDirectoryInput("gxfiles://");

        expectExportButtonEnabled();
    });

    it("should localize button text", async () => {
        const newLocal = wrapper.find(".export-button").text();
        // TODO: fix typing, this is a jest matcher with a custom expect
        // extension, or, just use vanilla javascript in test harness if there
        // isn't significant value in typing here?
        (expect(newLocal) as any).toBeLocalizationOf("Export");
    });

    it("should emit 'export' event with correct inputs on export button click", async () => {
        await setNameInput("export.tar.gz");
        await setDirectoryInput("gxfiles://");
        expect(wrapper.emitted()).not.toHaveProperty("export");

        await wrapper.find(".export-button").trigger("click");

        expect(wrapper.emitted()).toHaveProperty("export");
        expect(wrapper.emitted()["export"][0][0]).toBe("gxfiles://");
        expect(wrapper.emitted()["export"][0][1]).toBe("export.tar.gz");
    });

    it("should clear the inputs (hence disabling export) after export when clearInputAfterExport is enabled", async () => {
        await wrapper.setProps({
            clearInputAfterExport: true,
        });
        await setNameInput("export.tar.gz");
        await setDirectoryInput("gxfiles://");

        await wrapper.find(".export-button").trigger("click");

        expectExportButtonDisabled();
    });

    function expectExportButtonDisabled() {
        expect(wrapper.find(".export-button").exists()).toBeTruthy();
        expect(wrapper.find(".export-button").attributes("disabled")).toBeTruthy();
    }

    function expectExportButtonEnabled() {
        expect(wrapper.find(".export-button").exists()).toBeTruthy();
        expect(wrapper.find(".export-button").attributes("disabled")).toBeFalsy();
    }

    async function setNameInput(newValue: string) {
        const nameInput = wrapper.find("#name");
        await nameInput.setValue(newValue);
    }

    async function setDirectoryInput(newValue: string) {
        await wrapper.findComponent(FilesInput).vm.$emit("input", newValue);
    }
});
