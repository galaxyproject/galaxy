import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import Multiselect from "vue-multiselect";

import UploadSelect from "./UploadSelect.vue";

const localVue = getLocalVue();

function mountSelect() {
    return mount(UploadSelect as object, {
        propsData: {
            options: [
                { id: "hg19", text: "Human (hg19)" },
                { id: "mm10", text: "Mouse (mm10)" },
            ],
            value: "hg19",
        },
        localVue,
    });
}

describe("UploadSelect", () => {
    it("keeps the selection when backspace is pressed in an empty search", async () => {
        const wrapper = mountSelect();
        const multiselect = wrapper.findComponent(Multiselect);
        (multiselect.vm as unknown as { removeLastElement: () => void }).removeLastElement();
        await wrapper.vm.$nextTick();
        expect(wrapper.emitted("input")).toBeUndefined();
    });

    it("ignores a null selection", async () => {
        const wrapper = mountSelect();
        wrapper.findComponent(Multiselect).vm.$emit("input", null);
        await wrapper.vm.$nextTick();
        expect(wrapper.emitted("input")).toBeUndefined();
    });

    it("emits the id of a new selection", async () => {
        const wrapper = mountSelect();
        wrapper.findComponent(Multiselect).vm.$emit("input", { id: "mm10", text: "Mouse (mm10)" });
        await wrapper.vm.$nextTick();
        expect(wrapper.emitted("input")).toEqual([["mm10"]]);
    });
});
