import { createLocalVue, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import { defineComponent } from "vue";

import type ConfirmDialogComponent from "@/components/ConfirmDialog.vue";

import { type ConfirmDialogOptions, setConfirmDialogComponentRef, useConfirmDialog } from "./confirmDialog";

type ConfirmDialogInstance = InstanceType<typeof ConfirmDialogComponent>;

const localVue = createLocalVue();

describe("useConfirmDialog", () => {
    afterEach(() => {
        setConfirmDialogComponentRef(null);
    });

    it("cancels pending confirm when caller component unmounts", async () => {
        setConfirmDialogComponentRef({
            confirm: (_msg: string, options: ConfirmDialogOptions) =>
                new Promise<boolean>((resolve) => {
                    options.signal?.addEventListener("abort", () => resolve(false), { once: true });
                }),
        } as ConfirmDialogInstance);

        let confirm: ReturnType<typeof useConfirmDialog>["confirm"] = () => Promise.resolve(null);

        const CallerComponent = defineComponent({
            setup() {
                ({ confirm } = useConfirmDialog());
                return {};
            },
            template: "<div />",
        });

        const wrapper = mount(CallerComponent as object, { localVue });

        const promise = confirm("Are you sure?");

        wrapper.unmount(); // triggers onUnmounted → controller.abort()

        expect(await promise).toBe(false);
    });
});
