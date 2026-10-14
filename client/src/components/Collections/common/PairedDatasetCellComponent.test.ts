import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { describe, expect, it, vi } from "vitest";

import PairedDatasetCellComponent from "./PairedDatasetCellComponent.vue";

function mountPairedCell() {
    const context = { pinia: createPinia(), onSwap: vi.fn(), onUnpair: vi.fn() };
    const value = {
        forward: { id: "f", hid: 1, name: "reads_1.fastq" },
        reverse: { id: "r", hid: 2, name: "reads_2.fastq" },
    };
    const wrapper = mount(PairedDatasetCellComponent as object, {
        props: { params: { context, value } },
        global: getLocalVue(),
    });
    return { wrapper, context, value };
}

describe("PairedDatasetCellComponent", () => {
    it("swaps the pair from the swap button", async () => {
        const { wrapper, context, value } = mountPairedCell();
        await wrapper.find("button[title='Swap forward and reverse']").trigger("click");
        expect(context.onSwap).toHaveBeenCalledWith(value);
    });

    it("unpairs the pair from the unpair button", async () => {
        const { wrapper, context, value } = mountPairedCell();
        await wrapper.find("button[title='Unpair']").trigger("click");
        expect(context.onUnpair).toHaveBeenCalledWith(value);
    });
});
