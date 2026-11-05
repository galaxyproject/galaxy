import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import PairingFilterInputGroup from "./PairingFilterInputGroup.vue";

function mountGroup(forwardFilter = "_1", reverseFilter = "_2") {
    return mount(PairingFilterInputGroup, {
        props: { forwardFilter, reverseFilter },
        global: getLocalVue(),
    });
}

describe("PairingFilterInputGroup", () => {
    it("renders both filters in GFormInput fields", () => {
        const inputs = mountGroup().findAll("input");
        expect(inputs).toHaveLength(2);
        expect(inputs.map((input) => input.classes())).toEqual([
            expect.arrayContaining(["g-form-input"]),
            expect.arrayContaining(["g-form-input"]),
        ]);
        expect(inputs.map((input) => (input.element as HTMLInputElement).value)).toEqual(["_1", "_2"]);
    });

    it("emits on-update with both filters when one is typed", async () => {
        const wrapper = mountGroup();
        await wrapper.findAll("input")[0]!.setValue("_R1");
        expect(wrapper.emitted("on-update")?.at(-1)).toEqual(["_R1", "_2"]);
        await wrapper.findAll("input")[1]!.setValue("_R2");
        expect(wrapper.emitted("on-update")?.at(-1)).toEqual(["_R1", "_R2"]);
    });

    it("shows the new filters when the parent updates the props", async () => {
        const wrapper = mountGroup();
        await wrapper.setProps({ forwardFilter: ".1.fastq", reverseFilter: ".2.fastq" });
        const values = wrapper.findAll("input").map((input) => (input.element as HTMLInputElement).value);
        expect(values).toEqual([".1.fastq", ".2.fastq"]);
    });

    it("marks a filter that is not a valid regular expression invalid", () => {
        const inputs = mountGroup("_1[", "_2").findAll("input");
        expect(inputs[0]!.attributes("aria-invalid")).toBe("true");
        expect(inputs[1]!.attributes("aria-invalid")).toBeUndefined();
    });
});
