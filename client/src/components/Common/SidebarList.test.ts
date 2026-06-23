import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import SidebarList from "./SidebarList.vue";

interface TestItem {
    id: number;
    label: string;
}

const ITEMS: TestItem[] = [
    { id: 1, label: "Alpha" },
    { id: 2, label: "Beta" },
    { id: 3, label: "Gamma" },
];

function mountList(props: Record<string, unknown> = {}) {
    return mount(SidebarList as any, {
        propsData: {
            items: ITEMS,
            isLoading: false,
            itemKey: (item: TestItem) => item.id,
            ...props,
        },
        scopedSlots: {
            item: '<div slot-scope="{ item, index }">{{ item.label }}-{{ index }}</div>',
        },
        stubs: {
            FontAwesomeIcon: true,
        },
    });
}

describe("SidebarList", () => {
    describe("loading state", () => {
        it("shows loading indicator when isLoading is true", () => {
            const wrapper = mountList({ isLoading: true });
            expect(wrapper.find("[data-description='sidebar list loading']").exists()).toBe(true);
        });

        it("renders default loading message", () => {
            const wrapper = mountList({ isLoading: true });
            expect(wrapper.find("[data-description='sidebar list loading']").text()).toContain("Loading...");
        });

        it("renders custom loading message", () => {
            const wrapper = mountList({ isLoading: true, loadingMessage: "Fetching data..." });
            expect(wrapper.find("[data-description='sidebar list loading']").text()).toContain("Fetching data...");
        });

        it("does not render items when loading", () => {
            const wrapper = mountList({ isLoading: true });
            expect(wrapper.find(".sidebar-items").exists()).toBe(false);
        });

        it("does not render empty state when loading", () => {
            const wrapper = mountList({ isLoading: true, items: [] });
            expect(wrapper.find("[data-description='sidebar list empty']").exists()).toBe(false);
        });
    });

    describe("empty state", () => {
        it("shows empty message when items is empty", () => {
            const wrapper = mountList({ items: [] });
            expect(wrapper.find("[data-description='sidebar list empty']").exists()).toBe(true);
        });

        it("renders default empty message", () => {
            const wrapper = mountList({ items: [] });
            expect(wrapper.find("[data-description='sidebar list empty']").text()).toContain("No items found.");
        });

        it("renders custom empty message", () => {
            const wrapper = mountList({ items: [], emptyMessage: "Nothing here" });
            expect(wrapper.find("[data-description='sidebar list empty']").text()).toContain("Nothing here");
        });

        it("does not render items when empty", () => {
            const wrapper = mountList({ items: [] });
            expect(wrapper.find(".sidebar-items").exists()).toBe(false);
        });

        it("does not render loading state when empty", () => {
            const wrapper = mountList({ items: [] });
            expect(wrapper.find("[data-description='sidebar list loading']").exists()).toBe(false);
        });
    });

    describe("items rendering", () => {
        it("renders one sidebar-item per item", () => {
            const wrapper = mountList();
            expect(wrapper.findAll("[data-description='sidebar item']")).toHaveLength(3);
        });

        it("renders scoped slot content with correct item and index", () => {
            const wrapper = mountList();
            const items = wrapper.findAll("[data-description='sidebar item']");
            expect(items.at(0)!.text()).toContain("Alpha-0");
            expect(items.at(1)!.text()).toContain("Beta-1");
            expect(items.at(2)!.text()).toContain("Gamma-2");
        });

        it("does not render loading or empty states", () => {
            const wrapper = mountList();
            expect(wrapper.find("[data-description='sidebar list loading']").exists()).toBe(false);
            expect(wrapper.find("[data-description='sidebar list empty']").exists()).toBe(false);
        });
    });

    describe("interaction", () => {
        it("emits select with item, index, and event on click", async () => {
            const wrapper = mountList();
            const items = wrapper.findAll("[data-description='sidebar item']");
            await items.at(1)!.trigger("click");

            const emitted = wrapper.emitted("select")!;
            expect(emitted).toHaveLength(1);
            expect(emitted[0]![0]).toEqual(ITEMS[1]);
            expect(emitted[0]![1]).toBe(1);
            expect(emitted[0]![2]).toBeInstanceOf(MouseEvent);
        });

        it("emits select on Enter keydown", async () => {
            const wrapper = mountList();
            const items = wrapper.findAll("[data-description='sidebar item']");
            await items.at(0)!.trigger("keydown", { key: "Enter" });

            const emitted = wrapper.emitted("select")!;
            expect(emitted).toHaveLength(1);
            expect(emitted[0]![0]).toEqual(ITEMS[0]);
            expect(emitted[0]![1]).toBe(0);
        });

        it("does not emit select on non-Enter keydown", async () => {
            const wrapper = mountList();
            const items = wrapper.findAll("[data-description='sidebar item']");
            await items.at(0)!.trigger("keydown", { key: "Space" });
            expect(wrapper.emitted("select")).toBeFalsy();
        });
    });

    describe("accessibility", () => {
        it("each item has role=button", () => {
            const wrapper = mountList();
            const items = wrapper.findAll("[data-description='sidebar item']");
            items.wrappers.forEach((item) => {
                expect(item.attributes("role")).toBe("button");
            });
        });

        it("each item has tabindex=0", () => {
            const wrapper = mountList();
            const items = wrapper.findAll("[data-description='sidebar item']");
            items.wrappers.forEach((item) => {
                expect(item.attributes("tabindex")).toBe("0");
            });
        });
    });

    describe("itemClass prop", () => {
        it("applies class from itemClass function", () => {
            const wrapper = mountList({
                itemClass: (_item: TestItem, index: number) => ({ active: index === 1 }),
            });
            const items = wrapper.findAll("[data-description='sidebar item']");
            expect(items.at(0)!.classes()).not.toContain("active");
            expect(items.at(1)!.classes()).toContain("active");
            expect(items.at(2)!.classes()).not.toContain("active");
        });

        it("applies string class from itemClass function", () => {
            const wrapper = mountList({
                itemClass: (_item: TestItem, index: number) => (index === 0 ? "first" : undefined),
            });
            const items = wrapper.findAll("[data-description='sidebar item']");
            expect(items.at(0)!.classes()).toContain("first");
            expect(items.at(1)!.classes()).not.toContain("first");
        });
    });
});
