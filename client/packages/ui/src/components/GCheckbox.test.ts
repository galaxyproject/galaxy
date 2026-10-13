import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import { defineComponent, h, ref, withDirectives } from "vue";

import { vGTooltip } from "../directives/vGTooltip";

import GCheckbox from "./GCheckbox.vue";
import GCheckboxGroup from "./GCheckboxGroup.vue";

function mountWithModel(initial: boolean, attrs = ref<Record<string, unknown>>({})) {
    const checked = ref(initial);
    const Parent = defineComponent({
        setup() {
            return () =>
                h(GCheckbox, {
                    id: "test-checkbox",
                    modelValue: checked.value,
                    "onUpdate:modelValue": (value: boolean) => (checked.value = value),
                    ...attrs.value,
                });
        },
    });
    return { checked, wrapper: mount(Parent) };
}

describe("GCheckbox", () => {
    it("receives the bound value as modelValue", () => {
        const { wrapper } = mountWithModel(true);
        const checkbox = wrapper.findComponent(GCheckbox);

        expect(checkbox.props("modelValue")).toBe(true);
        expect(checkbox.attributes("value")).toBeUndefined();
        expect(wrapper.find("input").attributes("value")).toBeUndefined();
        expect((wrapper.find("input").element as HTMLInputElement).checked).toBe(true);
    });

    it("updates the bound value when toggled", async () => {
        const { checked, wrapper } = mountWithModel(false);

        await wrapper.find("input").setValue(true);
        expect(checked.value).toBe(true);
        expect(wrapper.findComponent(GCheckbox).emitted("update:modelValue")).toEqual([[true]]);

        await wrapper.find("input").setValue(false);
        expect(checked.value).toBe(false);
    });

    it("emits change with the native event", async () => {
        const { wrapper } = mountWithModel(false);

        await wrapper.find("input").setValue(true);
        const change = wrapper.findComponent(GCheckbox).emitted("change");
        expect(change).toHaveLength(1);
        expect(change![0]![0]).toBeInstanceOf(Event);
    });

    it("shows a partly-checked state while indeterminate", async () => {
        const wrapper = mount(GCheckbox, { props: { indeterminate: true } });
        const input = wrapper.get("input").element as HTMLInputElement;

        expect(input.indeterminate).toBe(true);

        await wrapper.setProps({ indeterminate: false });
        expect(input.indeterminate).toBe(false);
    });

    it("keeps class, style and title on the label and puts other attributes on the input", () => {
        const wrapper = mount(GCheckbox, {
            props: { modelValue: false },
            attrs: {
                class: "extra-class",
                style: "margin-top: 4px;",
                "data-test-id": "my-checkbox",
                title: "Select row",
                "aria-label": "Select row",
            },
        });
        const label = wrapper.find("label");
        const input = wrapper.find("input");

        expect(label.classes()).toContain("extra-class");
        expect(label.attributes("style")).toContain("margin-top: 4px");
        expect(label.attributes("data-test-id")).toBeUndefined();
        expect(label.attributes("title")).toBe("Select row");
        expect(input.attributes("data-test-id")).toBe("my-checkbox");
        expect(input.attributes("title")).toBeUndefined();
        expect(input.attributes("aria-label")).toBe("Select row");
        expect(input.classes()).not.toContain("extra-class");
    });

    it("prefers a caller data-test-id over the one derived from id", () => {
        const wrapper = mount(GCheckbox, {
            props: { id: "box", modelValue: false },
            attrs: { "data-test-id": "custom" },
        });

        expect(wrapper.find("label").attributes("data-test-id")).toBe("box-label");
        expect(wrapper.find("input").attributes("data-test-id")).toBe("custom");
    });

    it("updates input attributes when the parent changes them", async () => {
        const attrs = ref<Record<string, unknown>>({ "data-description": "First" });
        const { wrapper } = mountWithModel(false, attrs);
        expect(wrapper.find("input").attributes("data-description")).toBe("First");

        attrs.value = { "data-description": "Second" };
        await wrapper.vm.$nextTick();
        expect(wrapper.find("input").attributes("data-description")).toBe("Second");
    });

    it("picks up attributes added after mounting without any", async () => {
        const attrs = ref<Record<string, unknown>>({});
        const { wrapper } = mountWithModel(false, attrs);

        attrs.value = { class: "late-class", "data-description": "Late" };
        await wrapper.vm.$nextTick();
        expect(wrapper.find("label").classes()).toContain("late-class");
        expect(wrapper.find("input").attributes("data-description")).toBe("Late");
    });

    it("gives v-g-tooltip on the component its title", () => {
        const wrapper = mount(() =>
            withDirectives(h(GCheckbox, { modelValue: false, title: "Select all" }), [
                [vGTooltip, undefined, "", { hover: true }],
            ]),
        );

        expect(wrapper.get("label").element.dataset.gTooltipTitle).toBe("Select all");
        wrapper.unmount();
    });

    it("binds native listeners to the label so click modifiers cover the whole control", async () => {
        const targets: Array<EventTarget | null> = [];
        const onClick = vi.fn((event: Event) => targets.push(event.currentTarget));
        const wrapper = mount(GCheckbox, {
            props: { modelValue: false },
            attrs: { onClick },
            slots: { default: "Label text" },
        });

        await wrapper.find(".g-checkbox-label").trigger("click");
        expect(onClick).toHaveBeenCalled();
        expect(targets.every((target) => target === wrapper.find("label").element)).toBe(true);
    });

    it("renders as a switch in switch mode", () => {
        const wrapper = mount(GCheckbox, { props: { modelValue: false, switch: true } });

        expect(wrapper.classes()).toContain("g-switch");
        expect(wrapper.find("input").attributes("role")).toBe("switch");
    });

    it("keeps the native checkbox role outside switch mode", () => {
        const wrapper = mount(GCheckbox, { props: { modelValue: false } });

        expect(wrapper.classes()).not.toContain("g-switch");
        expect(wrapper.find("input").attributes("role")).toBeUndefined();
    });

    it("renders name, value and required on the input", () => {
        const wrapper = mount(GCheckbox, {
            props: { modelValue: false, name: "include", required: true, value: "hidden" },
        });
        const input = wrapper.find("input");

        expect(input.attributes("name")).toBe("include");
        expect(input.attributes("value")).toBe("hidden");
        expect(input.attributes("required")).toBeDefined();
        expect(wrapper.find("label").attributes("name")).toBeUndefined();
    });

    it("renders non-string values as their string form", () => {
        const wrapper = mount(GCheckbox, { props: { modelValue: false, value: 0 } });

        expect(wrapper.find("input").attributes("value")).toBe("0");
    });

    it.each([
        ["small", "g-small"],
        ["large", "g-large"],
    ] as const)("applies the %s size class", (size, className) => {
        const wrapper = mount(GCheckbox, { props: { modelValue: false, size } });

        expect(wrapper.find("label").classes()).toContain(className);
    });

    it("adds no size class by default", () => {
        const wrapper = mount(GCheckbox, { props: { modelValue: false } });

        expect(
            wrapper
                .find("label")
                .classes()
                .filter((name) => /^g-(small|medium|large)$/.test(name)),
        ).toEqual([]);
    });

    describe("inside a group", () => {
        function mountInGroup(childProps: Record<string, unknown>, groupProps: Record<string, unknown> = {}) {
            const wrapper = mount(GCheckboxGroup, {
                props: { modelValue: [], ...groupProps },
                slots: { default: () => h(GCheckbox, childProps, () => "Child") },
            });
            return { checkbox: wrapper.findComponent(GCheckbox), wrapper };
        }

        it("leaves the v-model to the group and still emits change", async () => {
            const { checkbox, wrapper } = mountInGroup({ value: "b" });

            await wrapper.find("input").setValue(true);
            expect(checkbox.emitted("update:modelValue")).toBeUndefined();
            expect(checkbox.emitted("change")).toHaveLength(1);
            expect(wrapper.emitted("update:modelValue")).toEqual([[["b"]]]);
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

        it("always follows the group's disabled and switch mode", () => {
            const { wrapper } = mountInGroup(
                { disabled: false, switch: false, value: "b" },
                { disabled: true, switches: true },
            );
            const input = wrapper.find("input");

            expect(input.attributes("disabled")).toBeDefined();
            expect(input.attributes("role")).toBe("switch");
            expect(wrapper.find("label").classes()).toEqual(expect.arrayContaining(["g-disabled", "g-switch"]));
        });

        it("ignores its own switch prop but keeps its own disabled", () => {
            const { wrapper } = mountInGroup(
                { disabled: true, switch: true, value: "b" },
                { disabled: false, switches: false },
            );
            const input = wrapper.find("input");

            expect(input.attributes("disabled")).toBeDefined();
            expect(input.attributes("role")).toBeUndefined();
            expect(wrapper.find("label").classes()).not.toContain("g-switch");
        });
    });
});
