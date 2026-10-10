import { emittedArg, getLocalVue } from "@tests/vitest/helpers";
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

function mountDrilldown({ multiple, value }) {
    return mount(FormDrilldown, {
        props: { id: "dd", value, options: OPTIONS, multiple },
        global: localVue,
    });
}

async function toggle(wrapper, name, checked) {
    await wrapper.get(`#drilldown-option-${name}`).setValue(checked);
}

describe("FormDrilldown", () => {
    it("submits only the chosen option when it has descendants", async () => {
        const wrapper = mountDrilldown({ multiple: true, value: [] });
        await toggle(wrapper, "a", true);

        expect(emittedArg(wrapper, "input")).toEqual(["a"]);
    });

    it("keeps other selections when adding one", async () => {
        const wrapper = mountDrilldown({ multiple: true, value: ["ba"] });
        await toggle(wrapper, "ab", true);

        expect(emittedArg(wrapper, "input")).toEqual(["ba", "ab"]);
    });

    it("removes only the deselected option, keeping its selected descendants", async () => {
        const wrapper = mountDrilldown({ multiple: true, value: ["a", "aa"] });
        await toggle(wrapper, "a", false);

        expect(emittedArg(wrapper, "input")).toEqual(["aa"]);
    });

    it("emits the chosen value alone when not multiple", async () => {
        const wrapper = mountDrilldown({ multiple: false, value: null });
        await toggle(wrapper, "aba", true);

        expect(emittedArg(wrapper, "input")).toBe("aba");
    });
});
