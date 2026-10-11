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
});
