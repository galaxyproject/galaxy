import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import Multiselect from "vue-multiselect";

import SingleItemSelector from "./SingleItemSelector.vue";

const localVue = getLocalVue();

const ITEMS = [
    { id: "a", text: "Alpha" },
    { id: "b", text: "Beta" },
    { id: "c", text: "Gamma" },
];

function mountComponent(propsData: object = {}) {
    return mount(SingleItemSelector as object, {
        propsData,
        localVue,
    });
}

describe("SingleItemSelector", () => {
    describe("loading state", () => {
        it("shows a loading message when loading is true", () => {
            const wrapper = mountComponent({ loading: true, collectionName: "Things" });
            const span = wrapper.findComponent({ name: "LoadingSpan" });
            expect(span.exists()).toBe(true);
            expect(span.props("message")).toBe("Loading Things...");
        });

        it("does not show the selector while loading", () => {
            const wrapper = mountComponent({ loading: true, items: ITEMS });
            expect(wrapper.findComponent({ name: "LoadingSpan" }).exists()).toBe(true);
        });
    });

    describe("empty items", () => {
        it("does not render the selector when items is empty", () => {
            const wrapper = mountComponent({ items: [] });
            expect(wrapper.findComponent(Multiselect).exists()).toBe(false);
        });

        it("does not render the selector when items prop is omitted", () => {
            const wrapper = mountComponent({});
            expect(wrapper.findComponent(Multiselect).exists()).toBe(false);
        });
    });

    describe("initial selection", () => {
        it("selects the first item by default when no currentItem is given", () => {
            const wrapper = mountComponent({ items: ITEMS });
            expect(wrapper.findComponent(Multiselect).props("value")).toEqual(ITEMS[0]);
        });

        it("selects the matching currentItem when provided", () => {
            const wrapper = mountComponent({ items: ITEMS, currentItem: ITEMS[1] });
            expect(wrapper.findComponent(Multiselect).props("value")).toEqual(ITEMS[1]);
        });

        it("falls back to the currentItem object itself when it is not in items", () => {
            const externalItem = { id: "z", text: "External" };
            const wrapper = mountComponent({ items: ITEMS, currentItem: externalItem });
            expect(wrapper.findComponent(Multiselect).props("value")).toEqual(externalItem);
        });
    });

    describe("emitting selection", () => {
        it("emits update:selected-item when an item is selected", async () => {
            const wrapper = mountComponent({ items: ITEMS });

            // Open the dropdown then click the third option
            await wrapper.find(".multiselect").trigger("click");
            const options = wrapper.findAll(".multiselect__option");
            await options.at(2).trigger("click");

            const emitted = wrapper.emitted("update:selected-item");
            expect(emitted).toBeTruthy();
            expect(emitted![0]![0]).toEqual(ITEMS[2]);
        });
    });

    describe("reactivity", () => {
        it("resets selection to first item when items prop changes", async () => {
            const wrapper = mountComponent({ items: ITEMS, currentItem: ITEMS[2] });

            const newItems = [
                { id: "x", text: "X-Ray" },
                { id: "y", text: "Yankee" },
            ];
            await wrapper.setProps({ items: newItems, currentItem: undefined });

            expect(wrapper.findComponent(Multiselect).props("value")).toEqual(newItems[0]);
        });

        it("updates selection when currentItem prop changes", async () => {
            const wrapper = mountComponent({ items: ITEMS, currentItem: ITEMS[0] });

            await wrapper.setProps({ currentItem: ITEMS[2] });

            expect(wrapper.findComponent(Multiselect).props("value")).toEqual(ITEMS[2]);
        });
    });
});
