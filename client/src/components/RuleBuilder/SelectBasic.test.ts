import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import VueMultiselect from "vue-multiselect";

import SelectBasic from "./SelectBasic.vue";

describe("SelectBasic", () => {
    // The rule builder shows several of these at once, so a fixed id would repeat.
    it("gives each select its own id", () => {
        const options = [{ id: "a", text: "A" }];
        const first = mount(SelectBasic as object, { props: { options } });
        const second = mount(SelectBasic as object, { props: { options } });

        const firstId = first.findComponent(VueMultiselect).props("id");
        expect(firstId).toBeTruthy();
        expect(second.findComponent(VueMultiselect).props("id")).not.toBe(firstId);
    });

    // Column ids are 0-based, so column A is a real selection, not an empty one.
    it("shows the first column as selected for a target of 0", () => {
        const options = [
            { id: 0, text: "A" },
            { id: 1, text: "B" },
        ];
        const wrapper = mount(SelectBasic as object, { props: { options, modelValue: 0 } });

        expect(wrapper.findComponent(VueMultiselect).props("modelValue")).toEqual({ id: 0, text: "A" });
    });
});
