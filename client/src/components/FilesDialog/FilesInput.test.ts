import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { filesDialog } from "@/utils/dataModals";

import FilesInput from "./FilesInput.vue";

vi.mock("@/utils/dataModals", () => ({
    filesDialog: vi.fn(),
}));

describe("FilesInput", () => {
    beforeEach(() => {
        vi.mocked(filesDialog).mockClear();
    });

    it("exposes selectFile to open the files dialog", () => {
        const wrapper = mount(FilesInput as object, {
            global: getLocalVue(),
            props: { value: "" },
        });
        (wrapper.vm as unknown as { selectFile: () => void }).selectFile();
        expect(filesDialog).toHaveBeenCalledOnce();
    });

    it("opens the files dialog when the input is clicked", async () => {
        const wrapper = mount(FilesInput as object, {
            global: getLocalVue(),
            props: { value: "" },
        });
        await wrapper.get("input").trigger("click");
        expect(filesDialog).toHaveBeenCalledOnce();
    });

    it("emits the typed path as input", async () => {
        const wrapper = mount(FilesInput as object, {
            global: getLocalVue(),
            props: { value: "" },
        });
        const input = wrapper.get("input.directory-form-input");
        expect(input.classes()).toContain("g-form-input");
        await input.setValue("gxftp://data");
        expect(wrapper.emitted("input")?.at(-1)).toEqual(["gxftp://data"]);
    });
});
