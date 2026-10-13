import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import { defineComponent, h, ref, toRaw } from "vue";

import type { SelectOption } from "./GSelect.types";

import GSelect from "./GSelect.vue";

const OPTIONS: SelectOption<string>[] = [
    { text: "Alpha", value: "a" },
    { text: "Bravo", value: "b" },
    { text: "Charlie", value: "c", disabled: true },
];

function mountWithModel(initial: unknown, selectProps: Record<string, unknown> = {}, slot?: () => unknown) {
    const selected = ref<unknown>(initial);
    const Parent = defineComponent({
        setup() {
            return () =>
                h(
                    GSelect,
                    {
                        modelValue: selected.value,
                        "onUpdate:modelValue": (value: unknown) => (selected.value = value),
                        ...selectProps,
                    },
                    slot ? { default: slot } : undefined,
                );
        },
    });
    return { selected, wrapper: mount(Parent) };
}

function selectElement(wrapper: ReturnType<typeof mount>) {
    return wrapper.get("select").element as HTMLSelectElement;
}

describe("GSelect", () => {
    it("receives the bound value as modelValue and selects the matching option", () => {
        const { wrapper } = mountWithModel("b", { options: OPTIONS });

        expect(wrapper.findComponent(GSelect).props()).toMatchObject({ modelValue: "b" });
        expect(selectElement(wrapper).value).toBe("b");
        expect(wrapper.findAll("option").map((option) => option.text())).toEqual(["Alpha", "Bravo", "Charlie"]);
    });

    it("updates the bound value when another option is chosen", async () => {
        const { selected, wrapper } = mountWithModel("a", { options: OPTIONS });

        await wrapper.get("select").setValue("b");

        expect(selected.value).toBe("b");
        expect(wrapper.findComponent(GSelect).emitted("update:modelValue")).toEqual([["b"]]);
    });

    it("emits change with the native event", async () => {
        const { wrapper } = mountWithModel("a", { options: OPTIONS });

        await wrapper.get("select").setValue("b");

        const change = wrapper.findComponent(GSelect).emitted("change");
        expect(change).toHaveLength(1);
        expect(change![0]![0]).toBeInstanceOf(Event);
    });

    it("keeps object and null option values as they are", async () => {
        const first = { id: "v1", name: "1.0" };
        const second = { id: "v2", name: "2.0" };
        const { selected, wrapper } = mountWithModel(null, {
            options: [
                { text: "None", value: null },
                { text: "1.0", value: first },
                { text: "2.0", value: second },
            ],
        });

        expect(selectElement(wrapper).selectedIndex).toBe(0);

        selectElement(wrapper).options[2]!.selected = true;
        await wrapper.get("select").trigger("change");
        expect(toRaw(selected.value)).toBe(second);

        selectElement(wrapper).options[0]!.selected = true;
        await wrapper.get("select").trigger("change");
        expect(selected.value).toBeNull();
    });

    it("selects an object value that is equal but not identical", () => {
        const { wrapper } = mountWithModel(
            { id: "v2" },
            {
                options: [
                    { text: "1", value: { id: "v1" } },
                    { text: "2", value: { id: "v2" } },
                ],
            },
        );

        expect(selectElement(wrapper).selectedIndex).toBe(1);
    });

    it("renders option children from the default slot after the options prop", async () => {
        const { selected, wrapper } = mountWithModel("y", { options: [{ text: "X", value: "x" }] }, () => [
            h("option", { value: "y" }, "Y"),
            h("option", { value: "z" }, "Z"),
        ]);

        expect(wrapper.findAll("option").map((option) => option.text())).toEqual(["X", "Y", "Z"]);
        expect(selectElement(wrapper).value).toBe("y");

        await wrapper.get("select").setValue("z");
        expect(selected.value).toBe("z");
    });

    it("disables single options and the whole select", () => {
        const { wrapper } = mountWithModel("a", { options: OPTIONS, disabled: true });

        expect(wrapper.findAll("option")[2]!.attributes("disabled")).toBeDefined();
        expect(selectElement(wrapper).disabled).toBe(true);
        expect(wrapper.get("select").classes()).toContain("g-disabled");
    });

    it("passes attributes through to the select", () => {
        const { wrapper } = mountWithModel("a", {
            options: OPTIONS,
            id: "my-select",
            class: "extra-class",
            style: "max-width: 300px;",
            "aria-label": "Pick one",
            "data-description": "my select",
        });
        const select = wrapper.get("select");

        expect(select.attributes("id")).toBe("my-select");
        expect(select.attributes("aria-label")).toBe("Pick one");
        expect(select.attributes("data-description")).toBe("my select");
        expect(select.attributes("style")).toContain("max-width: 300px");
        expect(select.classes()).toEqual(expect.arrayContaining(["g-select", "extra-class"]));
    });

    it("styles the size without setting the native size attribute", () => {
        const { wrapper } = mountWithModel("a", { options: OPTIONS, size: "small" });
        const select = wrapper.get("select");

        expect(select.classes()).toContain("g-small");
        expect(select.attributes("size")).toBeUndefined();
    });

    it("marks an invalid state for assistive technology", () => {
        const { wrapper } = mountWithModel("a", { options: OPTIONS, state: false });
        const select = wrapper.get("select");

        expect(select.attributes("aria-invalid")).toBe("true");
        expect(select.classes()).toContain("g-invalid");
    });

    it("leaves aria-invalid unset when the state is valid or unknown", () => {
        expect(
            mountWithModel("a", { options: OPTIONS, state: true }).wrapper.get("select").attributes(),
        ).not.toHaveProperty("aria-invalid");
        expect(mountWithModel("a", { options: OPTIONS }).wrapper.get("select").attributes()).not.toHaveProperty(
            "aria-invalid",
        );
    });

    it("is named by a label that points at its id", () => {
        const label = document.createElement("label");
        label.htmlFor = "labelled-select";
        label.textContent = "Version";
        document.body.append(label);
        const wrapper = mount(GSelect, {
            props: { modelValue: "a", options: OPTIONS },
            attrs: { id: "labelled-select" },
            attachTo: document.body,
        });
        const select = wrapper.get("select").element as HTMLSelectElement;

        expect(Array.from(select.labels).map((element) => element.textContent)).toEqual(["Version"]);
        wrapper.unmount();
        label.remove();
    });
});
