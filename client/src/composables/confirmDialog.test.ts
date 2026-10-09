import { getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";
import { defineComponent, h } from "vue";

import type ConfirmDialogComponent from "@/components/ConfirmDialog.vue";
import { ensureDefined } from "@/utils/assertions";

import { setConfirmDialogComponentRef, useConfirmDialog } from "./confirmDialog";

type ConfirmDialogInstance = InstanceType<typeof ConfirmDialogComponent>;

enableAutoUnmount(afterEach);

describe("useConfirmDialog", () => {
    afterEach(() => {
        setConfirmDialogComponentRef(null);
    });

    it("cancels a pending confirmation when its caller unmounts", async () => {
        const confirm = vi.fn<ConfirmDialogInstance["confirm"]>(
            (_message, options = {}) =>
                new Promise<boolean>((resolve) => {
                    options.signal?.addEventListener("abort", () => resolve(false), { once: true });
                }),
        );
        const dialog: Pick<ConfirmDialogInstance, "confirm"> = { confirm };
        // The registration API requires a component instance; this double only implements its exposed method.
        setConfirmDialogComponentRef(dialog as ConfirmDialogInstance);

        const CallerComponent = defineComponent({
            setup: useConfirmDialog,
            render: () => h("div"),
        });
        const wrapper = mount(CallerComponent, { global: getLocalVue() });
        const confirmation = wrapper.vm.confirm("Are you sure?");
        const signal = ensureDefined(confirm.mock.calls[0]?.[1]?.signal);
        expect(signal.aborted).toBe(false);

        wrapper.unmount();

        expect(signal.aborted).toBe(true);
        expect(await confirmation).toBe(false);
    });
});
