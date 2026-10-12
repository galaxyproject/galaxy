import { enableAutoUnmount, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import { nextTick } from "vue";

import { ConfirmDialog as confirmService, setConfirmDialogComponentRef } from "@/composables/confirmDialog";

import ConfirmDialogComponent from "./ConfirmDialog.vue";

describe("ConfirmDialog", () => {
    const mountTargets = new Set<HTMLElement>();

    afterEach(() => {
        setConfirmDialogComponentRef(null);
        for (const target of mountTargets) {
            target.remove();
        }
        mountTargets.clear();
    });
    enableAutoUnmount(afterEach);

    function mountDialog() {
        const target = document.createElement("div");
        mountTargets.add(target);
        document.body.appendChild(target);

        const wrapper = mount(ConfirmDialogComponent, { attachTo: target });
        setConfirmDialogComponentRef(wrapper.vm);
        return wrapper;
    }

    it("resolves true when OK is clicked", async () => {
        const wrapper = mountDialog();
        const promise = confirmService.confirm("Are you sure?");
        await wrapper.get('[data-description="confirm dialog ok"]').trigger("click");
        expect(await promise).toBe(true);
    });

    it("resolves false when Cancel is clicked", async () => {
        const wrapper = mountDialog();
        const promise = confirmService.confirm("Are you sure?");
        await wrapper.get('[data-description="confirm dialog cancel"]').trigger("click");
        expect(await promise).toBe(false);
    });

    it("resolves null when dialog is dismissed (closed without choosing)", async () => {
        const wrapper = mountDialog();
        const promise = confirmService.confirm("Are you sure?");
        wrapper.get("dialog").element.dispatchEvent(new Event("close"));
        expect(await promise).toBe(null);
    });

    it("renders message and respects custom options", async () => {
        const wrapper = mountDialog();
        const promise = confirmService.confirm("Delete this item?", { title: "Confirm deletion", okText: "Delete" });
        await nextTick();
        const dialogText = wrapper.get("dialog").text();
        expect(dialogText).toContain("Delete this item?");
        expect(dialogText).toContain("Confirm deletion");
        expect(dialogText).toContain("Delete");

        await wrapper.get('[data-description="confirm dialog cancel"]').trigger("click");
        await promise;
    });

    it("resolves first pending promise as false on concurrent call", async () => {
        const wrapper = mountDialog();
        const first = confirmService.confirm("First message");
        const second = confirmService.confirm("Second message");
        expect(await first).toBe(false);
        await wrapper.get('[data-description="confirm dialog cancel"]').trigger("click");
        await second;
    });

    it("resolves false when abort signal fires", async () => {
        mountDialog();
        const controller = new AbortController();
        const promise = confirmService.confirm("Are you sure?", { signal: controller.signal });
        controller.abort();
        expect(await promise).toBe(false);
    });
});
