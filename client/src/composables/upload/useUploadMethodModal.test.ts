import { createPinia, setActivePinia } from "pinia";
import { describe, expect, it, vi } from "vitest";
import { defineComponent, h, nextTick } from "vue";

import { useUploadMethodModal } from "./useUploadMethodModal";

vi.mock("@/components/Panels/Upload/UploadMethodModal.vue", () => ({
    default: defineComponent({
        props: { show: Boolean, config: Object, hideTips: Boolean },
        emits: ["update:show", "uploaded", "cancelled"],
        setup(props, { emit }) {
            return () =>
                props.show
                    ? h("div", { class: "stub-modal", "data-title": props.config?.title }, [
                          h("button", { class: "stub-cancel", onClick: () => emit("cancelled") }),
                          h("button", {
                              class: "stub-upload",
                              onClick: () => emit("uploaded", [{ id: "d1", name: "n", hid: 1, src: "hda" }]),
                          }),
                      ])
                    : null;
        },
    }),
}));

describe("useUploadMethodModal", () => {
    it("passes config to the modal and resolves on cancel, then on upload", async () => {
        setActivePinia(createPinia());
        const { openUploadModal } = useUploadMethodModal();

        const first = openUploadModal({ title: "First" });
        await nextTick();
        const host = document.getElementById("upload-method-modal-host");
        expect(host).not.toBeNull();
        expect(host!.querySelector(".stub-modal")?.getAttribute("data-title")).toBe("First");

        (host!.querySelector(".stub-cancel") as HTMLButtonElement).click();
        const cancelled = await first;
        expect(cancelled.cancelled).toBe(true);
        await nextTick();
        expect(host!.querySelector(".stub-modal")).toBeNull();

        const second = openUploadModal({ title: "Second" });
        await nextTick();
        expect(document.querySelectorAll("#upload-method-modal-host").length).toBe(1);
        expect(host!.querySelector(".stub-modal")?.getAttribute("data-title")).toBe("Second");
        (host!.querySelector(".stub-upload") as HTMLButtonElement).click();
        const uploaded = await second;
        expect(uploaded.cancelled).toBe(false);
        expect(uploaded.toDataOptions()[0]?.id).toBe("d1");
    });
});
