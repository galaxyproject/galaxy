import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { nextTick } from "vue";

import ConfirmDialog from "./ConfirmDialog.vue";

type ConfirmDialogVM = InstanceType<typeof ConfirmDialog>;

describe("ConfirmDialog", () => {
    let wrapper: ReturnType<typeof mount>;
    let vm: ConfirmDialogVM;

    beforeEach(() => {
        wrapper = mount(ConfirmDialog as object, { attachTo: document.body });
        vm = wrapper.vm as unknown as ConfirmDialogVM;
    });

    afterEach(() => {
        wrapper.destroy();
        document.body.innerHTML = "";
    });

    it("resolves true when OK is clicked", async () => {
        const promise = vm.confirm("Are you sure?");
        await wrapper.find('[data-description="confirm dialog ok"]').trigger("click");
        expect(await promise).toBe(true);
    });

    it("resolves false when Cancel is clicked", async () => {
        const promise = vm.confirm("Are you sure?");
        await wrapper.find('[data-description="confirm dialog cancel"]').trigger("click");
        expect(await promise).toBe(false);
    });

    it("resolves null when dialog is dismissed (closed without choosing)", async () => {
        const promise = vm.confirm("Are you sure?");
        wrapper.find("dialog").element.dispatchEvent(new Event("close"));
        expect(await promise).toBe(null);
    });

    it("renders message and respects custom options", async () => {
        vm.confirm("Delete this item?", { title: "Confirm deletion", okText: "Delete" });
        await nextTick();
        const dialogText = wrapper.find("dialog").text();
        expect(dialogText).toContain("Delete this item?");
        expect(dialogText).toContain("Confirm deletion");
        expect(dialogText).toContain("Delete");
    });

    it("resolves first pending promise as false on concurrent call", async () => {
        const first = vm.confirm("First message");
        const second = vm.confirm("Second message");
        expect(await first).toBe(false);
        // resolve second cleanly
        await wrapper.find('[data-description="confirm dialog cancel"]').trigger("click");
        await second;
    });

    it("resolves false when abort signal fires", async () => {
        const controller = new AbortController();
        const promise = vm.confirm("Are you sure?", { signal: controller.signal });
        controller.abort();
        expect(await promise).toBe(false);
    });
});
