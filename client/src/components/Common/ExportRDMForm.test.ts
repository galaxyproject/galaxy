import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";

import ExportRDMForm from "./ExportRDMForm.vue";
import RDMDestinationSelector from "@/components/Common/RDMDestinationSelector.vue";

const FAKE_RECORD_URI = "gxfiles://test-uri/test-record";

const { server, http } = useServerMock();

async function mountExportRDMForm(defaultFilename = "my-history") {
    server.use(
        http.get("/api/remote_files/plugins", ({ response }) => {
            return response(200).json([]);
        }),
    );
    const wrapper = mount(ExportRDMForm as object, {
        props: { defaultFilename },
        global: getLocalVue(true),
    });
    await flushPromises();
    return wrapper;
}

describe("ExportRDMForm.vue", () => {
    it("renders the file name as a required GFormInput with the default file name", async () => {
        const wrapper = await mountExportRDMForm();
        const fileNameInput = wrapper.get("input#file-name-input");
        expect(fileNameInput.classes()).toContain("g-form-input");
        expect(fileNameInput.attributes("required")).toBeDefined();
        expect((fileNameInput.element as HTMLInputElement).value).toBe("my-history");
    });

    it("exports to the selected record with the typed file name", async () => {
        const wrapper = await mountExportRDMForm();
        await wrapper.get("input#file-name-input").setValue("renamed.tar.gz");
        wrapper.findComponent(RDMDestinationSelector).vm.$emit("onRecordSelected", FAKE_RECORD_URI);
        await flushPromises();

        await wrapper.get("#export-button-new-record").trigger("click");

        expect(wrapper.emitted("export")?.at(-1)).toEqual([FAKE_RECORD_URI, "renamed.tar.gz"]);
    });

    it("keeps the export button disabled while the file name is empty", async () => {
        const wrapper = await mountExportRDMForm();
        wrapper.findComponent(RDMDestinationSelector).vm.$emit("onRecordSelected", FAKE_RECORD_URI);
        await wrapper.get("input#file-name-input").setValue("");

        expect(wrapper.get("#export-button-new-record").attributes("aria-disabled")).toBeTruthy();
    });
});
