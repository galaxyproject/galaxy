import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { setActivePinia } from "pinia";
import { describe, expect, it, vi } from "vitest";

import ListHeader from "./ListHeader.vue";

const localVue = getLocalVue();

const RECOMMENDED = { label: "Recommended", title: "Server order" };

function mountHeader(propsData: Record<string, unknown> = {}) {
    const pinia = createTestingPinia({ createSpy: vi.fn });
    setActivePinia(pinia);
    return mount(ListHeader as object, {
        localVue,
        pinia,
        propsData: { listId: "test", showSortOptions: true, ...propsData },
    });
}

function pressedSortIds(wrapper: ReturnType<typeof mountHeader>) {
    return wrapper
        .findAll("[id^='sortby-']")
        .wrappers.filter((button) => button.classes().includes("g-pressed"))
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
});
