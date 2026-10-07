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
