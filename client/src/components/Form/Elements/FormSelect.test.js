import "@/composables/__mocks__/filter";

import { createTestingPinia } from "@pinia/testing";
import { emittedArg, getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import FormSelect from "./FormSelect.vue";
import FormSelection from "./FormSelection.vue";

const localVue = getLocalVue(true);

const options = [
    ["label_1", "value_1"],
    ["label_2", "value_2"],
    ["label_3", ""],
    ["label_4", 99],
];
const optionLabels = ["label_1", "label_2", "label_3", "label_4"];

function mountFormSelection(propsData) {
    const pinia = createTestingPinia({ createSpy: vi.fn });

    return mount(FormSelection, {
        global: localVue,
        propsData: { options, ...propsData },
        pinia,
    });
}

/** vue-multiselect renders its option list only while open, and picking a single option closes it. */
async function openMultiselect(wrapper) {
    if (!wrapper.find(".multiselect__content-wrapper").exists()) {
        await wrapper.find(".multiselect__select").trigger("mousedown");
    }
}

async function listedLabels(wrapper) {
    await openMultiselect(wrapper);
    return wrapper.findAll("[data-option-value]").map((option) => option.text());
}

async function selectedLabels(wrapper) {
    await openMultiselect(wrapper);
    return wrapper.findAll(".multiselect__option--selected").map((option) => option.text());
}

async function clickOption(wrapper, label) {
    await openMultiselect(wrapper);
    const option = wrapper.findAll(".multiselect__option").find((candidate) => candidate.text() === label);
    if (!option) {
        throw new Error(`No option labelled "${label}".`);
    }
    await option.trigger("click");
}

describe("FormSelect", () => {
    describe("single select", () => {
        it("lists the options in order", async () => {
            const wrapper = mountFormSelection();

            expect(await listedLabels(wrapper)).toEqual(optionLabels);
        });

        it("selects the first option when a required select has no value", async () => {
            const wrapper = mountFormSelection();

            expect(emittedArg(wrapper, "input")).toBe("value_1");
            expect(await selectedLabels(wrapper)).toEqual([]);

            await wrapper.setProps({ value: "value_1" });

            expect(await selectedLabels(wrapper)).toEqual(["label_1"]);
        });

        it("offers and selects 'Nothing selected' while an optional select has no value", async () => {
            const wrapper = mountFormSelection({ optional: true });

            expect(await listedLabels(wrapper)).toEqual(["Nothing selected", ...optionLabels]);
            expect(await selectedLabels(wrapper)).toEqual(["Nothing selected"]);
            expect(wrapper.emitted("input")).toBeUndefined();
        });

        it("clears an optional select by picking 'Nothing selected'", async () => {
            const wrapper = mountFormSelection({ optional: true });
            await wrapper.setProps({ value: "value_1" });
            expect(await selectedLabels(wrapper)).toEqual(["label_1"]);

            await clickOption(wrapper, "Nothing selected");

            expect(emittedArg(wrapper, "input")).toBe(null);
            await wrapper.setProps({ value: null });
            expect(await selectedLabels(wrapper)).toEqual(["Nothing selected"]);
        });
    });

    describe("multi-select", () => {
        it("emits null when a required multi-select is fully cleared", async () => {
            const wrapper = mountFormSelection({ optional: false, multiple: true, value: ["value_1"] });
            expect(await selectedLabels(wrapper)).toEqual(["label_1"]);

            await clickOption(wrapper, "label_1");

            expect(emittedArg(wrapper, "input")).toBe(null);
        });

        it("does not offer 'Nothing selected' in an optional multi-select", async () => {
            const wrapper = mountFormSelection({ optional: true, multiple: true, value: ["value_1", "", 99] });

            expect(await listedLabels(wrapper)).toEqual(optionLabels);
        });

        it("emits the remaining values as options are deselected, null once none are left, and reselects", async () => {
            const wrapper = mountFormSelection({ optional: true, multiple: true, value: ["value_1", "", 99] });
            expect(await selectedLabels(wrapper)).toEqual(["label_1", "label_3", "label_4"]);

            await clickOption(wrapper, "label_1");
            const withoutFirst = emittedArg(wrapper, "input");
            expect(withoutFirst).toEqual(["", 99]);
            await wrapper.setProps({ value: withoutFirst });

            await clickOption(wrapper, "label_3");
            const onlyNumeric = emittedArg(wrapper, "input", 1);
            expect(onlyNumeric).toEqual([99]);
            await wrapper.setProps({ value: onlyNumeric });

            await clickOption(wrapper, "label_4");
            const cleared = emittedArg(wrapper, "input", 2);
            expect(cleared).toBe(null);
            await wrapper.setProps({ value: cleared });

            await clickOption(wrapper, "label_1");
            expect(emittedArg(wrapper, "input", 3)).toEqual(["value_1"]);
        });
    });
});

describe("FormSelect accessible names", () => {
    it("does not name the search input after its id", () => {
        const wrapper = mountFormSelection();
        const input = wrapper.find("input.multiselect__input");
        expect(input.exists()).toBe(true);
        expect(input.attributes("aria-label")).toBeUndefined();
    });

    it("gives each instance its own default id", () => {
        const formSelectOptions = [{ label: "label_1", value: "value_1" }];
        const ids = [0, 1].map(() => {
            const wrapper = mount(FormSelect, { global: localVue, props: { options: formSelectOptions } });
            return wrapper.find("input.multiselect__input").attributes("id");
        });
        expect(ids[0]).toMatch(/^form-select-/);
        expect(ids[0]).not.toBe(ids[1]);
    });
});
