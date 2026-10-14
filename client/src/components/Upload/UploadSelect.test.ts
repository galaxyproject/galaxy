import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import Multiselect from "vue-multiselect";

import UploadSelect from "./UploadSelect.vue";

const localVue = getLocalVue();

const OPTIONS = ["csfasta", "fasta", "fastq"].map((id) => ({ id, text: id }));

function mountComponent(props: object = {}) {
    return mount(UploadSelect, {
        props: { options: OPTIONS, ...props },
        global: localVue,
    });
}

describe("UploadSelect", () => {
    it("emits the id of the selected option", async () => {
        const wrapper = mountComponent({ value: "fasta" });

        await wrapper.find(".multiselect").trigger("focus");
        await wrapper.findAll(".multiselect__option")[2]!.trigger("click");

        expect(wrapper.emitted("input")).toEqual([["fastq"]]);
    });

    it("keeps the current value when the selected option is clicked again", async () => {
        const wrapper = mountComponent({ value: "fasta" });

        await wrapper.find(".multiselect").trigger("focus");
        await wrapper.find(".multiselect__option--selected").trigger("click");

        expect(wrapper.emitted("input")).toBeUndefined();
    });

    it("keeps the current value when backspace is pressed in an empty search", async () => {
        const wrapper = mountComponent({ value: "fasta" });

        await wrapper.find(".multiselect").trigger("focus");
        await wrapper.find(".multiselect__input").trigger("keydown.delete");

        expect(wrapper.emitted("input")).toBeUndefined();
    });

    it("ignores a null selection", () => {
        const wrapper = mountComponent({ value: "fasta" });

        wrapper.findComponent(Multiselect).vm.$emit("input", null);

        expect(wrapper.emitted("input")).toBeUndefined();
    });

    it("lists the option whose id matches exactly first", async () => {
        const dbKeys = [
            { id: "hg19_rCRS", text: "Human (hg19 with rCRS)" },
            { id: "hg19", text: "Human Feb. 2009 (GRCh37/hg19) (hg19)" },
        ];
        const wrapper = mountComponent({ options: dbKeys });

        await wrapper.find(".multiselect").trigger("focus");
        await wrapper.find(".multiselect__input").setValue("hg19");

        const multiselect = wrapper.findComponent(Multiselect);
        expect((multiselect.props("options") as { id: string }[]).map((option) => option.id)).toEqual([
            "hg19",
            "hg19_rCRS",
        ]);
    });
});
