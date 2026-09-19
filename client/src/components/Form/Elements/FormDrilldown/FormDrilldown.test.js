import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import FormDrilldown from "./FormDrilldown.vue";

const localVue = getLocalVue();

const OPTIONS = [
    {
        name: "a",
        value: "a",
        options: [
            { name: "aa", value: "aa", options: [] },
            { name: "ab", value: "ab", options: [{ name: "aba", value: "aba", options: [] }] },
        ],
    },
    { name: "b", value: "b", options: [{ name: "ba", value: "ba", options: [] }] },
];

function mountDrilldown(multiple, value) {
    return mount(FormDrilldown, {
        propsData: { id: "dd", value, options: OPTIONS, multiple },
        localVue,
    });
}

async function toggle(wrapper, name, checked) {
    const input = wrapper.find(`#drilldown-option-${name}`);
    await input.setChecked(checked);
}

describe("FormDrilldown", () => {
    it("submits only the chosen option when it has descendants", async () => {
        const wrapper = mountDrilldown(true, []);
        await toggle(wrapper, "a", true);
        expect(wrapper.emitted().input[0][0]).toEqual(["a"]);
    });

    it("keeps other selections when adding one", async () => {
        const wrapper = mountDrilldown(true, ["ba"]);
        await toggle(wrapper, "ab", true);
        expect(wrapper.emitted().input[0][0]).toEqual(["ba", "ab"]);
    });

    it("removes only the deselected option", async () => {
        const wrapper = mountDrilldown(true, ["a", "aa"]);
        await toggle(wrapper, "a", false);
        expect(wrapper.emitted().input[0][0]).toEqual(["aa"]);
    });

    it("emits a bare value when not multiple", async () => {
        const wrapper = mountDrilldown(false, null);
        await toggle(wrapper, "aba", true);
        expect(wrapper.emitted().input[0][0]).toBe("aba");
    });
});
