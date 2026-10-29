import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import { defineComponent, h, ref } from "vue";

import type { RadioGroupOption } from "./radioGroupContext";

import GRadio from "./GRadio.vue";
import GRadioGroup from "./GRadioGroup.vue";

const OPTIONS: RadioGroupOption[] = [
    { text: "Alpha", value: "a" },
    { text: "Bravo", value: "b" },
    { text: "Charlie", value: "c" },
];

function mountWithModel(initial: unknown, groupProps: Record<string, unknown> = {}, slot?: () => unknown) {
    const selected = ref<unknown>(initial);
    const Parent = defineComponent({
        setup() {
            return () =>
                h(
                    GRadioGroup,
                    {
                        modelValue: selected.value,
                        "onUpdate:modelValue": (value: unknown) => (selected.value = value),
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

function checkedStates(wrapper: ReturnType<typeof mount>) {
    return inputs(wrapper).map((input) => (input.element as HTMLInputElement).checked);
}

describe("GRadioGroup", () => {
    it("checks the option whose value is the v-model", () => {
        const { wrapper } = mountWithModel("b", { options: OPTIONS });

        expect(wrapper.findComponent(GRadioGroup).props()).toMatchObject({ modelValue: "b" });
        expect(checkedStates(wrapper)).toEqual([false, true, false]);
        expect(wrapper.findAll(".g-radio-label").map((label) => label.text())).toEqual(["Alpha", "Bravo", "Charlie"]);
    });

    it("sets the v-model to the selected option's value", async () => {
        const { selected, wrapper } = mountWithModel("a", { options: OPTIONS });

        await inputs(wrapper)[2]!.setValue(true);
        expect(selected.value).toBe("c");
        expect(wrapper.findComponent(GRadioGroup).emitted("update:modelValue")).toEqual([["c"]]);
        expect(checkedStates(wrapper)).toEqual([false, false, true]);
    });

    it("matches values loosely, like BFormRadioGroup", () => {
        const { wrapper } = mountWithModel("2", {
            options: [
                { text: "One", value: 1 },
                { text: "Two", value: 2 },
            ],
        });

        expect(checkedStates(wrapper)).toEqual([false, true]);
    });

    it("keeps boolean option values", async () => {
        const { selected, wrapper } = mountWithModel(true, {
            options: [
                { text: "Yes", value: true },
                { text: "No", value: false },
            ],
        });
        expect(checkedStates(wrapper)).toEqual([true, false]);

        await inputs(wrapper)[1]!.setValue(true);
        expect(selected.value).toBe(false);
    });

    it("works with GRadio children in the default slot", async () => {
        const { selected, wrapper } = mountWithModel("x", {}, () => [
            h(GRadio, { value: "x" }, () => "X"),
            h(GRadio, { value: "y" }, () => "Y"),
        ]);

        expect(checkedStates(wrapper)).toEqual([true, false]);
        await inputs(wrapper)[1]!.setValue(true);
        expect(selected.value).toBe("y");
    });

    it("renders each option's value and a shared generated name on the inputs", () => {
        const { wrapper } = mountWithModel(undefined, { options: OPTIONS });
        const names = inputs(wrapper).map((input) => input.attributes("name"));

        expect(inputs(wrapper).map((input) => input.attributes("type"))).toEqual(["radio", "radio", "radio"]);
        expect(inputs(wrapper).map((input) => input.attributes("value"))).toEqual(["a", "b", "c"]);
        expect(names[0]).toMatch(/^g-radio-group-\d+$/);
        expect(new Set(names).size).toBe(1);
    });

    it("gives separate groups separate names and honors an explicit name", () => {
        const first = mountWithModel(undefined, { options: OPTIONS }).wrapper;
        const second = mountWithModel(undefined, { options: OPTIONS }).wrapper;
        const named = mountWithModel(undefined, { name: "format", options: OPTIONS }).wrapper;

        expect(inputs(first)[0]!.attributes("name")).not.toBe(inputs(second)[0]!.attributes("name"));
        expect(inputs(named).map((input) => input.attributes("name"))).toEqual(["format", "format", "format"]);
    });

    it("disables single options or the whole group", () => {
        const single = mountWithModel(undefined, {
            options: [
                { text: "On", value: "on" },
                { text: "Off", value: "off", disabled: true },
            ],
        }).wrapper;
        expect(inputs(single).map((input) => input.attributes("disabled") !== undefined)).toEqual([false, true]);

        const whole = mountWithModel(undefined, { disabled: true, options: OPTIONS }).wrapper;
        expect(whole.find("fieldset").attributes("disabled")).toBeDefined();
        expect(inputs(whole).every((input) => input.attributes("disabled") !== undefined)).toBe(true);
        expect(whole.findAll("label").every((label) => label.classes().includes("g-disabled"))).toBe(true);
    });

    it("lays options out inline unless stacked", () => {
        const inline = mountWithModel(undefined, { options: OPTIONS }).wrapper;
        const stacked = mountWithModel(undefined, { options: OPTIONS, stacked: true }).wrapper;

        expect(inline.find(".g-radio-group-options").classes()).not.toContain("g-stacked");
        expect(stacked.find(".g-radio-group-options").classes()).toContain("g-stacked");
    });

    it("passes its size to its radios", () => {
        const { wrapper } = mountWithModel(undefined, { options: OPTIONS, size: "small" });

        expect(wrapper.findAll("label").every((label) => label.classes().includes("g-small"))).toBe(true);
    });

    describe("button mode", () => {
        it("renders radios as grey buttons by default and marks the selected one", () => {
            const { wrapper } = mountWithModel("b", { buttons: true, options: OPTIONS });
            const labels = wrapper.findAll("label");

            expect(wrapper.find(".g-radio-group-options").classes()).toContain("g-buttons");
            expect(labels.every((label) => label.classes().includes("g-radio-button"))).toBe(true);
            expect(labels.every((label) => label.classes().includes("g-grey"))).toBe(true);
            expect(labels.map((label) => label.classes().includes("g-checked"))).toEqual([false, true, false]);
        });

        it("maps an outline variant to the color and outline classes", () => {
            const { wrapper } = mountWithModel(undefined, {
                buttons: true,
                buttonVariant: "outline-blue",
                options: OPTIONS,
            });
            const label = wrapper.find("label");

            expect(label.classes()).toEqual(expect.arrayContaining(["g-radio-button", "g-blue", "g-outline"]));
        });

        it("keeps the native radio input for keyboard and assistive technology", async () => {
            const { selected, wrapper } = mountWithModel("a", { buttons: true, options: OPTIONS });

            expect(inputs(wrapper).map((input) => input.attributes("type"))).toEqual(["radio", "radio", "radio"]);
            await inputs(wrapper)[1]!.setValue(true);
            expect(selected.value).toBe("b");
        });

        it("renders plain radios when buttons is off", () => {
            const { wrapper } = mountWithModel(undefined, { buttonVariant: "blue", options: OPTIONS });

            expect(wrapper.find("label").classes()).not.toContain("g-radio-button");
            expect(wrapper.find("label").classes()).not.toContain("g-blue");
        });
    });

    describe("accessible name and role", () => {
        it("is a radiogroup", () => {
            const { wrapper } = mountWithModel(undefined, { options: OPTIONS });

            expect(wrapper.element.tagName).toBe("FIELDSET");
            expect(wrapper.attributes("role")).toBe("radiogroup");
        });

        it("names the group with a legend for the label prop", () => {
            const { wrapper } = mountWithModel(undefined, { label: "Format", options: OPTIONS });
            const legend = wrapper.find("fieldset > legend");

            expect(legend.text()).toBe("Format");
            expect(wrapper.attributes("aria-labelledby")).toBe(legend.attributes("id"));
        });

        it("names the group with a legend for the label slot", () => {
            const wrapper = mount(GRadioGroup, { props: { options: OPTIONS }, slots: { label: "Slotted label" } });
            const legend = wrapper.find("fieldset > legend");

            expect(legend.text()).toBe("Slotted label");
            expect(wrapper.attributes("aria-labelledby")).toBe(legend.attributes("id"));
        });

        it("renders the description under the options and links it with aria-describedby", () => {
            const { wrapper } = mountWithModel(undefined, {
                label: "Format",
                description: "Pick one.",
                options: OPTIONS,
            });

            const description = wrapper.find("fieldset > small");
            expect(description.text()).toBe("Pick one.");
            expect(wrapper.attributes("aria-describedby")).toBe(description.attributes("id"));
            // the last child of the fieldset, so it reads after the options
            expect(wrapper.element.lastElementChild).toBe(description.element);
        });

        it("renders no description and no aria-describedby by default", () => {
            const { wrapper } = mountWithModel(undefined, { options: OPTIONS });

            expect(wrapper.find("fieldset > small").exists()).toBe(false);
            expect(wrapper.attributes("aria-describedby")).toBeUndefined();
        });

        it("puts legendClass on the legend, not on the group", () => {
            const { wrapper } = mountWithModel(undefined, { label: "Format", legendClass: "pb-0", options: OPTIONS });

            expect(wrapper.find("fieldset > legend").classes()).toContain("pb-0");
            expect(wrapper.classes()).not.toContain("pb-0");
        });

        it("adds only the enabled legendClass entries to the legend", () => {
            const { wrapper } = mountWithModel(undefined, {
                label: "Format",
                legendClass: { "mb-2": false, "pb-0": true },
                options: OPTIONS,
            });
            const legend = wrapper.find("fieldset > legend");

            expect(legend.classes()).toContain("pb-0");
            expect(legend.classes()).not.toContain("mb-2");
        });

        it("passes aria-labelledby and aria-describedby from the caller to the group", () => {
            const { wrapper } = mountWithModel(undefined, {
                "aria-describedby": "outside-help",
                "aria-labelledby": "outside-title",
                options: OPTIONS,
            });

            expect(wrapper.find("legend").exists()).toBe(false);
            expect(wrapper.attributes("aria-labelledby")).toBe("outside-title");
            expect(wrapper.attributes("aria-describedby")).toBe("outside-help");
        });
    });

    describe("GRadio inside the group", () => {
        function mountInGroup(childProps: Record<string, unknown>, groupProps: Record<string, unknown> = {}) {
            const wrapper = mount(GRadioGroup, {
                props: { modelValue: "a", ...groupProps },
                slots: { default: () => h(GRadio, childProps, () => "Child") },
            });
            return { radio: wrapper.findComponent(GRadio), wrapper };
        }

        it("leaves the v-model to the group and still emits change", async () => {
            const { radio, wrapper } = mountInGroup({ value: "b" });

            await wrapper.find("input").setValue(true);
            expect(radio.emitted("update:modelValue")).toBeUndefined();
            expect(radio.emitted("change")).toHaveLength(1);
            expect(wrapper.emitted("update:modelValue")).toEqual([["b"]]);
        });

        it("ignores its own modelValue in favor of the group's", () => {
            const { wrapper } = mountInGroup({ modelValue: "b", value: "b" });

            expect((wrapper.find("input").element as HTMLInputElement).checked).toBe(false);
        });

        it("lets its own name and size win over the group's", () => {
            const { wrapper } = mountInGroup(
                { name: "own", size: "large", value: "b" },
                { name: "shared", size: "small" },
            );

            expect(wrapper.find("input").attributes("name")).toBe("own");
            expect(wrapper.find("label").classes()).toContain("g-large");
            expect(wrapper.find("label").classes()).not.toContain("g-small");
        });

        it("always follows the group's disabled", () => {
            const { wrapper } = mountInGroup({ disabled: false, value: "b" }, { disabled: true });

            expect(wrapper.find("input").attributes("disabled")).toBeDefined();
        });
    });
});
