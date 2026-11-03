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

function mountDrilldown(multiple, value) {
    return mount(FormDrilldown, {
        propsData: { id: "dd", value, options: OPTIONS, multiple },
        localVue,
    });
}

async function toggle(wrapper, name, checked) {
    const input = wrapper.find(`#drilldown-option-${name}`);
    await input.setValue(checked);
}

describe("FormDrilldown", () => {
    it("submits only the chosen option when it has descendants", async () => {
        const wrapper = mountDrilldown(true, []);
        await toggle(wrapper, "a", true);
        expect(emittedArg(wrapper, "input")).toEqual(["a"]);
    });

    it("keeps other selections when adding one", async () => {
        const wrapper = mountDrilldown(true, ["ba"]);
        await toggle(wrapper, "ab", true);
        expect(emittedArg(wrapper, "input")).toEqual(["ba", "ab"]);
    });

    it("removes only the deselected option", async () => {
        const wrapper = mountDrilldown(true, ["a", "aa"]);
        await toggle(wrapper, "a", false);
        expect(emittedArg(wrapper, "input")).toEqual(["aa"]);
    });

    it("emits a bare value when not multiple", async () => {
        const wrapper = mountDrilldown(false, null);
        await toggle(wrapper, "aba", true);
        expect(emittedArg(wrapper, "input")).toBe("aba");
    });

    it("checks the options in the current value", () => {
        const wrapper = mountDrilldown(true, ["aa", "ba"]);
        expect(wrapper.find("#drilldown-option-aa").element.checked).toBe(true);
        expect(wrapper.find("#drilldown-option-ba").element.checked).toBe(true);
        expect(wrapper.find("#drilldown-option-ab").element.checked).toBe(false);
    });

    it("selects every value from select all", async () => {
        const wrapper = mountDrilldown(true, []);
        await wrapper.find(".select-all-checkbox input").setValue(true);
        expect([...emittedArg(wrapper, "input")].sort()).toEqual(["a", "aa", "ab", "aba", "b", "ba"]);
    });

    it("clears the value from select all", async () => {
        const wrapper = mountDrilldown(true, ["a", "aa", "ab", "aba", "b", "ba"]);
        const selectAll = wrapper.find(".select-all-checkbox input");
        expect(selectAll.element.checked).toBe(true);
        await selectAll.setValue(false);
        expect(emittedArg(wrapper, "input")).toBeNull();
    });

    it("marks select all as partly checked when some values are selected", () => {
        const wrapper = mountDrilldown(true, ["aa"]);
        expect(wrapper.find(".select-all-checkbox input").element.indeterminate).toBe(true);
    });

    it("gives single-select radios one shared name for keyboard navigation", () => {
        const wrapper = mountDrilldown(false, "ab");
        const radios = wrapper.findAll("input[type=radio]");
        expect(radios.length).toBe(6);
        const names = new Set(radios.map((radio) => radio.attributes("name")));
        expect(names.size).toBe(1);
        expect([...names][0]).toBeTruthy();
        expect(wrapper.find("#drilldown-option-ab").element.checked).toBe(true);
        expect(wrapper.find(".select-all-checkbox").exists()).toBe(false);
    });

    it("keeps the radios of two drilldowns with the same id in separate groups", async () => {
        const mountSingle = (value) =>
            mount(FormDrilldown, {
                props: { id: "dd", value, options: OPTIONS, multiple: false },
                global: localVue,
                attachTo: document.body,
            });
        const first = mountSingle("a");
        const second = mountSingle("b");
        const firstName = first.find("input[type=radio]").attributes("name");
        const secondName = second.find("input[type=radio]").attributes("name");
        expect(firstName).toBeTruthy();
        expect(firstName).not.toBe(secondName);
        await first.find("#drilldown-option-aa").setValue(true);
        expect(second.find("#drilldown-option-b").element.checked).toBe(true);
        first.unmount();
        second.unmount();
    });
});
