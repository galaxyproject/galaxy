import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, describe, expect, it, vi } from "vitest";
import { h } from "vue";

import { SingleQueryProvider } from "./SingleQueryProvider";
import { SimpleProviderMixin } from "./storeProviders";

const localVue = getLocalVue();

// Renderless providers hand back the slot content, so a multi-node slot gives them a fragment root.
const slots = { default: () => [h("span", "first"), h("span", "second")] };

function extraneousAttrsWarnings(spy) {
    return spy.mock.calls.filter((args) => String(args[0]).includes("Extraneous non-props attributes"));
}

describe("renderless providers", () => {
    afterEach(() => {
        vi.restoreAllMocks();
    });

    it("SingleQueryProvider passes its attributes to the lookup without a fallthrough warning", async () => {
        const warn = vi.spyOn(console, "warn");
        const lookup = vi.fn().mockResolvedValue({ name: "dataset" });
        const Provider = SingleQueryProvider(lookup);

        const wrapper = mount(Provider, { attrs: { id: "dataset_id", view: "element" }, slots, global: localVue });
        await flushPromises();

        expect(lookup.mock.calls[0][0]).toEqual({ id: "dataset_id", view: "element" });
        expect(wrapper.findAll("span")).toHaveLength(2);
        expect(extraneousAttrsWarnings(warn)).toEqual([]);
    });

    it("SimpleProviderMixin does not warn about attributes it does not declare", async () => {
        const warn = vi.spyOn(console, "warn");
        const Provider = {
            mixins: [SimpleProviderMixin],
            methods: {
                async load() {},
            },
        };

        const wrapper = mount(Provider, {
            props: { id: "item_id" },
            attrs: { view: "element" },
            slots,
            global: localVue,
        });
        await flushPromises();

        expect(wrapper.findAll("span")).toHaveLength(2);
        expect(extraneousAttrsWarnings(warn)).toEqual([]);
    });
});

describe("renderless providers with Vue 3 slots", () => {
    // compat reads compatConfig off the mounted component itself, so this copy runs without $scopedSlots.
    function withoutScopedSlots(component) {
        return { ...component, compatConfig: { ...component.compatConfig, INSTANCE_SCOPED_SLOTS: false } };
    }

    const scopedSlot = { default: ({ loading, result }) => h("span", loading ? "loading" : result.name) };

    it("SingleQueryProvider hands its result to the default slot", async () => {
        const Provider = withoutScopedSlots(SingleQueryProvider(vi.fn().mockResolvedValue({ name: "dataset" })));

        const wrapper = mount(Provider, { attrs: { id: "dataset_id" }, slots: scopedSlot, global: localVue });
        await flushPromises();

        expect(wrapper.find("span").text()).toBe("dataset");
    });

    it("SingleQueryProvider keeps class, style and its listeners out of the lookup and the cache key", async () => {
        const lookup = vi.fn().mockResolvedValue({ name: "dataset" });
        const Provider = SingleQueryProvider(lookup);
        // As Vue 3 does, put class, style and undeclared listeners in $attrs.
        const component = {
            ...Provider,
            compatConfig: { ...Provider.compatConfig, INSTANCE_ATTRS_CLASS_STYLE: false, INSTANCE_LISTENERS: false },
        };
        const listeners = { onError: vi.fn(), "onUpdate:result": vi.fn() };

        mount(component, {
            props: { useCache: true },
            attrs: { id: "dataset_id", class: "first", style: "color: red", ...listeners },
            slots: scopedSlot,
            global: localVue,
        });
        mount(component, {
            props: { useCache: true },
            attrs: { id: "dataset_id", class: "second", ...listeners },
            slots: scopedSlot,
            global: localVue,
        });
        await flushPromises();

        expect(lookup).toHaveBeenCalledTimes(1);
        expect(lookup.mock.calls[0][0]).toEqual({ id: "dataset_id" });
        expect(listeners["onUpdate:result"]).toHaveBeenCalledWith({ name: "dataset" });
    });

    it("SimpleProviderMixin hands its item to the default slot", async () => {
        const Provider = withoutScopedSlots({
            mixins: [SimpleProviderMixin],
            methods: {
                async load() {
                    this.item = { name: "item" };
                },
            },
        });

        const wrapper = mount(Provider, { props: { id: "item_id" }, slots: scopedSlot, global: localVue });
        await flushPromises();

        expect(wrapper.find("span").text()).toBe("item");
    });
});
