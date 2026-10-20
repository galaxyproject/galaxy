import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import UploadTableNameCell from "./UploadTableNameCell.vue";

function mountCell(props: { value: string; state?: boolean | null }) {
    return mount(UploadTableNameCell, { props, global: getLocalVue() });
}

describe("UploadTableNameCell", () => {
    it("renders the name in a GFormInput and emits the typed name as a string", async () => {
        const wrapper = mountCell({ value: "reads.fastq" });
        const input = wrapper.get("input");
        expect(input.classes()).toContain("g-form-input");
        expect(input.element.value).toBe("reads.fastq");

        await input.setValue("renamed.fastq");
        expect(wrapper.emitted("input")).toEqual([["renamed.fastq"]]);
    });

    it("marks the input invalid when the state is false", () => {
        const wrapper = mountCell({ value: "", state: false });
        expect(wrapper.get("input").attributes("aria-invalid")).toBe("true");
    });

    it("emits blur when the input loses focus", async () => {
        const wrapper = mountCell({ value: "reads.fastq" });
        await wrapper.get("input").trigger("blur");
        expect(wrapper.emitted("blur")).toHaveLength(1);
    });
});
