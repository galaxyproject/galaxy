import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { describe, expect, it, vi } from "vitest";

import ListHeader from "./ListHeader.vue";

const localVue = getLocalVue();

const RECOMMENDED = { label: "Recommended", title: "Server order" };

const COLUMN_MENU = {
    listId: "datasets",
    showSortOptions: false,
    columnOptions: [
        { key: "name", label: "Name" },
        { key: "size", label: "Size" },
    ],
    visibleColumns: ["name"],
};

function mountHeader(propsData: Record<string, unknown> = {}, options: { attachTo?: HTMLElement } = {}) {
    const pinia = createTestingPinia({ createSpy: vi.fn });
    setActivePinia(pinia);
    return mount(ListHeader as object, {
        localVue,
        pinia,
        propsData: { listId: "test", showSortOptions: true, ...propsData },
        ...options,
    });
}

async function pressKey(target: Element, key: string) {
    target.dispatchEvent(new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true }));
    await flushPromises();
}

function pressedSortIds(wrapper: ReturnType<typeof mountHeader>) {
    return wrapper
        .findAll("[id^='sortby-']")
        .filter((button) => button.classes().includes("g-pressed"))
        .map((button) => button.attributes("id"));
}

describe("ListHeader", () => {
    it("starts on update time with no default sort option", () => {
        const wrapper = mountHeader();

        expect(wrapper.find("#sortby-default").exists()).toBe(false);
        expect(pressedSortIds(wrapper)).toEqual(["sortby-update_time"]);
    });

    it("toggles direction when the active sort is clicked again", async () => {
        const wrapper = mountHeader();

        await wrapper.find("#sortby-update_time").trigger("click");
        await wrapper.find("#sortby-name").trigger("click");

        expect(wrapper.emitted("sort-changed")).toEqual([
            ["update_time", false],
            ["name", true],
        ]);
    });

    it("starts on the default sort option when one is given", () => {
        const wrapper = mountHeader({ defaultSortOption: RECOMMENDED });

        const button = wrapper.find("#sortby-default");
        // GButton renders its tooltip title inside the button.
        expect(button.text()).toContain("Recommended");
        expect(button.text()).toContain("Server order");
        expect(pressedSortIds(wrapper)).toEqual(["sortby-default"]);
        expect(wrapper.emitted("sort-changed")).toBeUndefined();
    });

    it("sorts descending on the first click away from the default", async () => {
        const wrapper = mountHeader({ defaultSortOption: RECOMMENDED });

        await wrapper.find("#sortby-update_time").trigger("click");

        expect(wrapper.emitted("sort-changed")).toEqual([["update_time", true]]);
        expect(pressedSortIds(wrapper)).toEqual(["sortby-update_time"]);
    });

    it("returns to the default sort option", async () => {
        const wrapper = mountHeader({ defaultSortOption: RECOMMENDED });

        await wrapper.find("#sortby-name").trigger("click");
        await wrapper.find("#sortby-default").trigger("click");

        expect(wrapper.emitted("sort-default")).toHaveLength(1);
        expect(pressedSortIds(wrapper)).toEqual(["sortby-default"]);

        // It has no direction, so clicking it again does nothing.
        await wrapper.find("#sortby-default").trigger("click");
        expect(wrapper.emitted("sort-default")).toHaveLength(1);

        // And leaving it again starts descending, whatever the direction was before.
        await wrapper.find("#sortby-name").trigger("click");
        expect(wrapper.emitted("sort-changed")).toEqual([
            ["name", true],
            ["name", true],
        ]);
    });

    it("keeps the column chooser header inside a named group of the menu", () => {
        const wrapper = mountHeader({
            listId: "datasets",
            showSortOptions: false,
            columnOptions: [
                { key: "name", label: "Name" },
                { key: "size", label: "Size" },
            ],
            visibleColumns: ["name"],
        });

        expect(wrapper.get(".dropdown-toggle").attributes("aria-label")).toBe("Columns");
        const group = wrapper.get("[role='menu'] > [role='group']");
        expect(group.attributes("aria-label")).toBe("Show/Hide Columns");
        const header = group.get(".dropdown-header");
        expect(header.attributes("role")).toBe("presentation");
        expect(header.find("button").exists()).toBe(true);
    });

    it("emits select-all from the select all checkbox", async () => {
        const wrapper = mountHeader({ showSelectAll: true });
        const checkbox = wrapper.get("input#list-header-select-all");

        await checkbox.setValue(true);

        expect(wrapper.emitted("select-all")).toHaveLength(1);
    });

    it("toggles a column once from its menu item and leaves the checked state to the prop", async () => {
        const wrapper = mountHeader(COLUMN_MENU);
        const items = () => wrapper.findAll("[role='menuitemcheckbox']");
        expect(items().map((item) => item.text())).toEqual(["Name", "Size"]);
        expect(items().map((item) => item.attributes("aria-checked"))).toEqual(["true", "false"]);

        await items()[1]!.trigger("click");

        expect(wrapper.emitted("toggle-column")).toEqual([["size"]]);
        expect(items()[1]!.attributes("aria-checked")).toBe("false");

        await wrapper.setProps({ visibleColumns: ["name", "size"] } as object);

        expect(items()[1]!.attributes("aria-checked")).toBe("true");
        expect(items()[1]!.get<HTMLInputElement>("input[type='checkbox']").element.checked).toBe(true);
    });

    it("toggles a column once with Space", async () => {
        const wrapper = mountHeader(COLUMN_MENU, { attachTo: document.body });

        await pressKey(wrapper.get(".dropdown-toggle").element, "ArrowDown");
        await pressKey(document.activeElement!, " ");
        expect(wrapper.emitted("toggle-column")).toEqual([["size"]]);

        wrapper.unmount();
    });
});
