import { getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, describe, expect, it, onTestFinished, vi } from "vitest";

import GModal from "./GModal.vue";

const localVue = getLocalVue();

describe("GModal", () => {
    afterEach(() => {
        vi.restoreAllMocks();
    });
    enableAutoUnmount(afterEach);

    it("does not open an already open dialog again", async () => {
        const showModal = vi.spyOn(HTMLDialogElement.prototype, "showModal");
        const target = document.createElement("div");
        document.body.appendChild(target);
        onTestFinished(() => target.remove());
        const wrapper = mount(GModal, {
            global: localVue,
            props: { show: true, title: "Title" },
            attachTo: target,
        });
        await flushPromises();
        expect(showModal).toHaveBeenCalledOnce();
        expect(wrapper.get("button.g-modal-close-button").attributes("aria-label")).toBe("Close dialog");
        wrapper.vm.showModal();
        expect(showModal).toHaveBeenCalledOnce();
        wrapper.unmount();
    });
});
