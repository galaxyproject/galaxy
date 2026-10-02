import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import Multiselect from "vue-multiselect";

import UploadSelect from "./UploadSelect.vue";

const localVue = getLocalVue();

const OPTIONS = ["csfasta", "fasta", "fastq"].map((id) => ({ id, text: id }));

function mountComponent(propsData: object = {}) {
    return mount(UploadSelect as object, {
        propsData: { options: OPTIONS, ...propsData },
        localVue,
    });
}

describe("UploadSelect", () => {
    it("emits the id of the selected option", async () => {
        const wrapper = mountComponent({ value: "fasta" });

        await wrapper.find(".multiselect").trigger("click");
        await wrapper.findAll(".multiselect__option").at(2).trigger("click");

        expect(wrapper.emitted("input")).toEqual([["fastq"]]);
    });

    it("keeps the current value when the selected option is clicked again", async () => {
        const wrapper = mountComponent({ value: "fasta" });

        await wrapper.find(".multiselect").trigger("click");
        await wrapper.find(".multiselect__option--selected").trigger("click");

        expect(wrapper.emitted("input")).toBeUndefined();
    });

    it("keeps the current value when backspace is pressed in an empty search", async () => {
        const wrapper = mountComponent({ value: "fasta" });

        await wrapper.find(".multiselect").trigger("click");
        await wrapper.find(".multiselect__input").trigger("keydown.delete");

        expect(wrapper.emitted("input")).toBeUndefined();
    });

    it("ignores a null selection", () => {
        const wrapper = mountComponent({ value: "fasta" });

        wrapper.findComponent(Multiselect).vm.$emit("input", null);

        expect(wrapper.emitted("input")).toBeUndefined();
    });
});
