import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import type { BrowsableFilesSourcePlugin } from "@/api/remoteFiles";

import ExportRemoteSourceSelector from "./ExportRemoteSourceSelector.vue";

const WRITABLE_FILE_SOURCE: BrowsableFilesSourcePlugin = {
    id: "test-posix-source",
    type: "posix",
    uri_root: "gxfiles://test-posix-source",
    label: "Test Posix Source",
    doc: "Writable test source",
    writable: true,
    browsable: true,
    supports: { pagination: false, search: false, sorting: false, recursive: true },
};

const { server, http } = useServerMock();

async function mountSelector(fileName = "my-export") {
    server.use(
        http.get("/api/remote_files/plugins", ({ response }) => {
            return response(200).json([WRITABLE_FILE_SOURCE]);
        }),
    );
    const wrapper = mount(ExportRemoteSourceSelector, {
        props: { directory: "", fileName, fileExtension: "rocrate.zip", showFileName: true },
        global: getLocalVue(),
    });
    await flushPromises();
    return wrapper;
}

describe("ExportRemoteSourceSelector.vue", () => {
    it("renders the file name prop in a required GFormInput", async () => {
        const wrapper = await mountSelector();
        const fileNameInput = wrapper.get("[data-test-id='export-file-name-input']");
        expect(fileNameInput.element.tagName).toBe("INPUT");
        expect(fileNameInput.classes()).toContain("g-form-input");
        expect(fileNameInput.attributes("required")).toBeDefined();
        expect((fileNameInput.element as HTMLInputElement).value).toBe("my-export");
        expect(wrapper.text()).toContain(".rocrate.zip");
    });

    it("emits update:file-name with the typed file name", async () => {
        const wrapper = await mountSelector();
        await wrapper.get("[data-test-id='export-file-name-input']").setValue("renamed");
        expect(wrapper.emitted("update:file-name")?.at(-1)).toEqual(["renamed"]);
    });

    it("shows the new file name when the parent updates the prop", async () => {
        const wrapper = await mountSelector();
        await wrapper.setProps({ fileName: "from-parent" });
        const fileNameInput = wrapper.get("[data-test-id='export-file-name-input']");
        expect((fileNameInput.element as HTMLInputElement).value).toBe("from-parent");
    });
});
