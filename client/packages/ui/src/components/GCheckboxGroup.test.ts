import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import { defineComponent, h, ref } from "vue";

import type { CheckboxGroupOption } from "./checkboxGroupContext";

import GCheckbox from "./GCheckbox.vue";
import GCheckboxGroup from "./GCheckboxGroup.vue";

const OPTIONS: CheckboxGroupOption[] = [
    { text: "Alpha", value: "a" },
    { text: "Bravo", value: "b" },
    { text: "Charlie", value: "c" },
];

function mountWithModel(initial: unknown[], groupProps: Record<string, unknown> = {}, slot?: () => unknown) {
    const selected = ref<unknown[]>(initial);
    const Parent = defineComponent({
        setup() {
            return () =>
                h(
                    GCheckboxGroup,
                    {
                        modelValue: selected.value,
                        "onUpdate:modelValue": (value: unknown[]) => (selected.value = value),
                        ...groupProps,
                    },
                    slot ? { default: slot } : undefined,
                );
        },
    });
    return { selected, wrapper: mount(Parent) };
}

function inputs(wrapper: ReturnType<typeof mount>) {
    return wrapper.findAll("input");
}

describe("GCheckboxGroup", () => {
    it("checks the options whose values are in the v-model", () => {
        const { wrapper } = mountWithModel(["b"], { options: OPTIONS });
        const checked = inputs(wrapper).map((input) => (input.element as HTMLInputElement).checked);

        expect(wrapper.findComponent(GCheckboxGroup).props("modelValue")).toEqual(["b"]);
        expect(checked).toEqual([false, true, false]);
    });

    it("appends values in click order and removes unchecked ones", async () => {
        const { selected, wrapper } = mountWithModel([], { options: OPTIONS });
        const [alpha, bravo, charlie] = inputs(wrapper);

        await alpha!.setValue(true);
        await charlie!.setValue(true);
        await bravo!.setValue(true);
        expect(selected.value).toEqual(["a", "c", "b"]);

        await charlie!.setValue(false);
        expect(selected.value).toEqual(["a", "b"]);
    });

    it("emits a new array instead of mutating the bound one", async () => {
        const initial = ["a"];
        const { wrapper } = mountWithModel(initial, { options: OPTIONS });

        await inputs(wrapper)[1]!.setValue(true);
        const emitted = wrapper.findComponent(GCheckboxGroup).emitted("update:modelValue")!;
        expect(emitted[0]![0]).toEqual(["a", "b"]);
        expect(emitted[0]![0]).not.toBe(initial);
        expect(initial).toEqual(["a"]);
    });

    it("matches values loosely, like BFormCheckboxGroup", () => {
        const { wrapper } = mountWithModel(["2"], {
            options: [
                { text: "One", value: 1 },
                { text: "Two", value: 2 },
            ],
        });

        expect(inputs(wrapper).map((input) => (input.element as HTMLInputElement).checked)).toEqual([false, true]);
    });

    it("works with GCheckbox children in the default slot", async () => {
        const { selected, wrapper } = mountWithModel(["x"], {}, () => [
            h(GCheckbox, { value: "x" }, () => "X"),
            h(GCheckbox, { value: "y" }, () => "Y"),
        ]);
        const [x, y] = inputs(wrapper);

        expect((x!.element as HTMLInputElement).checked).toBe(true);
        await y!.setValue(true);
        await x!.setValue(false);
        expect(selected.value).toEqual(["y"]);
    });

    it("renders each option's value and a shared generated name on the inputs", () => {
        const { wrapper } = mountWithModel([], { options: OPTIONS });
        const names = inputs(wrapper).map((input) => input.attributes("name"));

        expect(inputs(wrapper).map((input) => input.attributes("value"))).toEqual(["a", "b", "c"]);
        expect(names[0]).toMatch(/^g-checkbox-group-\d+$/);
        expect(new Set(names).size).toBe(1);
    });

    it("gives separate groups separate names and honors an explicit name", () => {
        const first = mountWithModel([], { options: OPTIONS }).wrapper;
        const second = mountWithModel([], { options: OPTIONS }).wrapper;
        const named = mountWithModel([], { name: "datatypes", options: OPTIONS }).wrapper;

        expect(inputs(first)[0]!.attributes("name")).not.toBe(inputs(second)[0]!.attributes("name"));
        expect(inputs(named).map((input) => input.attributes("name"))).toEqual(["datatypes", "datatypes", "datatypes"]);
    });

    it("disables single options or the whole group", () => {
        const single = mountWithModel([], {
            options: [
                { text: "On", value: "on" },
                { text: "Off", value: "off", disabled: true },
            ],
        }).wrapper;
        expect(inputs(single).map((input) => input.attributes("disabled") !== undefined)).toEqual([false, true]);

        const whole = mountWithModel([], { disabled: true, options: OPTIONS }).wrapper;
        expect(whole.find("fieldset").attributes("disabled")).toBeDefined();
        expect(inputs(whole).every((input) => input.attributes("disabled") !== undefined)).toBe(true);
        expect(whole.findAll("label").every((label) => label.classes().includes("g-disabled"))).toBe(true);
    });

    it("passes switch mode and size to its checkboxes", () => {
        const { wrapper } = mountWithModel([], { options: OPTIONS, size: "small", switches: true });

        expect(inputs(wrapper).every((input) => input.attributes("role") === "switch")).toBe(true);
        expect(wrapper.findAll("label").every((label) => label.classes().includes("g-small"))).toBe(true);
    });

    it("lays options out inline unless stacked", () => {
        const inline = mountWithModel([], { options: OPTIONS }).wrapper;
        const stacked = mountWithModel([], { options: OPTIONS, stacked: true }).wrapper;

        expect(inline.find(".g-checkbox-group-options").classes()).not.toContain("g-stacked");
        expect(stacked.find(".g-checkbox-group-options").classes()).toContain("g-stacked");
    });

    describe("accessible name", () => {
        it("uses a legend for the label prop", () => {
            const { wrapper } = mountWithModel([], { label: "Options", options: OPTIONS });

            expect(wrapper.element.tagName).toBe("FIELDSET");
            expect(wrapper.find("fieldset > legend").text()).toBe("Options");
        });

        it("uses a legend for the label slot", () => {
            const wrapper = mount(GCheckboxGroup, { props: { options: OPTIONS }, slots: { label: "Slotted label" } });

            expect(wrapper.find("fieldset > legend").text()).toBe("Slotted label");
        });

        it("renders no legend without a label and passes aria attributes to the fieldset", () => {
            const { wrapper } = mountWithModel([], { "aria-labelledby": "outside-title", options: OPTIONS });

            expect(wrapper.find("legend").exists()).toBe(false);
            expect(wrapper.find("fieldset").attributes("aria-labelledby")).toBe("outside-title");
        });
    });
});
