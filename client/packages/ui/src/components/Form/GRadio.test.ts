import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import { defineComponent, h, ref } from "vue";

import GRadio from "./GRadio.vue";

function mountPair(initial: unknown, values: [unknown, unknown] = ["a", "b"]) {
    const selected = ref<unknown>(initial);
    const Parent = defineComponent({
        setup() {
            return () =>
                h(
                    "div",
                    values.map((value, index) =>
                        h(
                            GRadio,
                            {
                                id: `radio-${index}`,
                                modelValue: selected.value,
                                name: "pair",
                                value,
                                "onUpdate:modelValue": (next: unknown) => (selected.value = next),
                            },
                            () => `Option ${index}`,
                        ),
                    ),
                );
        },
    });
    return { selected, wrapper: mount(Parent) };
}

function checkedStates(wrapper: ReturnType<typeof mount>) {
    return wrapper.findAll("input").map((input) => (input.element as HTMLInputElement).checked);
}

describe("GRadio", () => {
    it("is checked when its value equals the v-model", () => {
        const { wrapper } = mountPair("b");

        expect(wrapper.findAllComponents(GRadio)[1]!.props("modelValue")).toBe("b");
        expect(checkedStates(wrapper)).toEqual([false, true]);
    });

    it("matches values loosely, like BFormRadio", () => {
        expect(checkedStates(mountPair("2", [1, 2]).wrapper)).toEqual([false, true]);
        expect(checkedStates(mountPair(false, [true, false]).wrapper)).toEqual([false, true]);
    });

    it("emits its own value, not the event, as the new v-model", async () => {
        const { selected, wrapper } = mountPair("a", [0, 1]);

        await wrapper.findAll("input")[1]!.setValue(true);
        expect(selected.value).toBe(1);
        expect(wrapper.findAllComponents(GRadio)[1]!.emitted("update:modelValue")).toEqual([[1]]);
        expect(checkedStates(wrapper)).toEqual([false, true]);
    });

    it("emits change with the native event", async () => {
        const { wrapper } = mountPair("a");

        await wrapper.findAll("input")[1]!.setValue(true);
        const change = wrapper.findAllComponents(GRadio)[1]!.emitted("change");
        expect(change).toHaveLength(1);
        expect(change![0]![0]).toBeInstanceOf(Event);
    });

    it("renders a native radio with name and value", () => {
        const { wrapper } = mountPair(undefined, ["a", 0]);
        const inputs = wrapper.findAll("input");

        expect(inputs.map((input) => input.attributes("type"))).toEqual(["radio", "radio"]);
        expect(inputs.map((input) => input.attributes("name"))).toEqual(["pair", "pair"]);
        expect(inputs.map((input) => input.attributes("value"))).toEqual(["a", "0"]);
    });

    it("labels the input with its slot text", () => {
        const { wrapper } = mountPair("a");
        const label = wrapper.findAll("label")[0]!;

        expect(label.find("input").exists()).toBe(true);
        expect(label.find(".g-radio-label").text()).toBe("Option 0");
    });

    it("keeps class, style and title on the label and puts other attributes on the input", () => {
        const wrapper = mount(GRadio, {
            props: { modelValue: "a", value: "a" },
            attrs: {
                class: "extra-class",
                style: "margin-top: 4px;",
                "data-test-id": "my-radio",
                title: "Pick me",
                "aria-describedby": "help",
            },
        });
        const label = wrapper.find("label");
        const input = wrapper.find("input");

        expect(label.classes()).toContain("extra-class");
        expect(label.attributes("style")).toContain("margin-top: 4px");
        expect(label.attributes("title")).toBe("Pick me");
        expect(label.attributes("data-test-id")).toBeUndefined();
        expect(input.attributes("data-test-id")).toBe("my-radio");
        expect(input.attributes("aria-describedby")).toBe("help");
        expect(input.attributes("title")).toBeUndefined();
        expect(input.classes()).not.toContain("extra-class");
    });

    it("derives data-test-id from id unless the caller sets one", () => {
        const derived = mount(GRadio, { props: { id: "box", value: "a" } });
        const custom = mount(GRadio, { props: { id: "box", value: "a" }, attrs: { "data-test-id": "custom" } });

        expect(derived.find("label").attributes("data-test-id")).toBe("box-label");
        expect(derived.find("input").attributes("data-test-id")).toBe("box-input");
        expect(derived.find("input").attributes("id")).toBe("box");
        expect(custom.find("input").attributes("data-test-id")).toBe("custom");
    });

    it("binds native listeners to the label", async () => {
        const onClick = vi.fn();
        const wrapper = mount(GRadio, { props: { value: "a" }, attrs: { onClick }, slots: { default: "Text" } });

        await wrapper.find(".g-radio-label").trigger("click");
        expect(onClick).toHaveBeenCalled();
    });

    it("renders disabled and required on the input", () => {
        const wrapper = mount(GRadio, { props: { disabled: true, required: true, value: "a" } });

        expect(wrapper.find("input").attributes("disabled")).toBeDefined();
        expect(wrapper.find("input").attributes("required")).toBeDefined();
        expect(wrapper.find("label").classes()).toContain("g-disabled");
    });

    it("takes an accessible name from aria-label when it has no visible label", () => {
        const wrapper = mount(GRadio, { props: { ariaLabel: "First row", value: 1 } });

        expect(wrapper.find("input").attributes("aria-label")).toBe("First row");
        expect(wrapper.find(".g-radio-label").exists()).toBe(false);
    });

    it.each([
        ["small", "g-small"],
        ["large", "g-large"],
    ] as const)("applies the %s size class", (size, className) => {
        const wrapper = mount(GRadio, { props: { size, value: "a" } });

        expect(wrapper.find("label").classes()).toContain(className);
    });
});
