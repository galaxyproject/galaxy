import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, describe, expect, it, vi } from "vitest";

import GModal from "./GModal.vue";

const localVue = getLocalVue();

describe("GModal", () => {
    afterEach(() => {
        vi.restoreAllMocks();
    });

    it("does not open an already open dialog again", async () => {
        const showModal = vi.spyOn(HTMLDialogElement.prototype, "showModal");
        const wrapper = mount(GModal as object, {
            localVue,
            propsData: { show: true, title: "Title" },
            attachTo: document.body,
        });
        await flushPromises();
        expect(showModal).toHaveBeenCalledOnce();
        (wrapper.vm as unknown as { showModal: () => void }).showModal();
        expect(showModal).toHaveBeenCalledOnce();
        wrapper.destroy();
    });
});
