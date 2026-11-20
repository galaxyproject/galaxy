import { mount, shallowMount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import { defineComponent, inject } from "vue";

const ShowsProvided = defineComponent({
    props: { label: { type: String, default: "" } },
    setup() {
        return { provided: inject("value", "missing") };
    },
    template: `<span>{{ label }} {{ provided }}</span>`,
});

describe("vue-test-utils adapter", () => {
    it.each([
        { option: "mocks", hint: "`mocks` → `global.mocks`" },
        { option: "provide", hint: "`provide` → `global.provide`" },
        { option: "listeners", hint: "`listeners` → `attrs` (as `onEvent` handlers)" },
        { option: "scopedSlots", hint: "`scopedSlots` → `slots`" },
        { option: "attachToDocument", hint: "`attachToDocument` → `attachTo`" },
    ])("rejects top-level `$option` and points to its v2 replacement", ({ option, hint }) => {
        const expected = `Unsupported top-level mount option(s), which Vue Test Utils v2 ignores. Use instead: ${hint}.`;

        expect(() => mount(ShowsProvided, { [option]: {} } as any)).toThrow(expected);
        expect(() => shallowMount(ShowsProvided, { [option]: {} } as any)).toThrow(expected);
    });

    it("lists every unsupported option in one error", () => {
        expect(() => mount(ShowsProvided, { mocks: {}, directives: {} } as any)).toThrow(
            "Use instead: `mocks` → `global.mocks`, `directives` → `global.directives`.",
        );
    });

    it("accepts v1 options it translates", () => {
        const wrapper = mount(ShowsProvided, {
            propsData: { label: "hello" },
            stubs: {},
            localVue: { provide: { value: "from localVue" } },
        } as any);

        expect(wrapper.text()).toBe("hello from localVue");
    });

    it("accepts v2 options", () => {
        const wrapper = mount(ShowsProvided, {
            props: { label: "hello" },
            global: { provide: { value: "from global" } },
        });

        expect(wrapper.text()).toBe("hello from global");
    });
});
