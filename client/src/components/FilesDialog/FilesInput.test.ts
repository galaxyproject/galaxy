import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import { filesDialog } from "@/utils/dataModals";

import FilesInput from "./FilesInput.vue";

vi.mock("@/utils/dataModals", () => ({
    filesDialog: vi.fn(),
}));

vi.mock("vue-router/composables", () => ({
    useRouter: vi.fn(() => ({ push: vi.fn() })),
}));

const localVue = getLocalVue();

describe("FilesInput", () => {
    it("exposes selectFile to open the files dialog", () => {
        const wrapper = mount(FilesInput as object, {
            localVue,
            propsData: { value: "" },
        });
        (wrapper.vm as unknown as { selectFile: () => void }).selectFile();
        expect(filesDialog).toHaveBeenCalledOnce();
    });
});
