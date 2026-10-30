import "@testing-library/jest-dom/vitest";

import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import GTable from "./GTable.vue";

const localVue = getLocalVue();

const rowDetailsSlot = '<div class="details-body" slot-scope="props">{{ props.item.body }}</div>';

function checkbox(element: Element | undefined) {
    return element as HTMLInputElement;
}

describe("GTable sorting", () => {
    it("keeps row selection on the same item after local sort", () => {
        const wrapper = mount(GTable as object, {
            localVue,
            pinia: createTestingPinia({ createSpy: vi.fn }),
            propsData: {
                items: [
                    { id: "c", name: "c.txt" },
                    { id: "a", name: "a.txt" },
                    { id: "b", name: "b.txt" },
                ],
                fields: [{ key: "name", label: "Name", sortable: true }],
                primaryKey: "id",
                selectable: true,
                selectedItems: [0],
                sortBy: "name",
            },
            attachTo: document.body,
        });

        const checkboxes = wrapper.findAll("tbody input").wrappers.map((row) => checkbox(row.element));

        expect(checkboxes[0]!.checked).toBe(false);
        expect(checkboxes[1]!.checked).toBe(false);
        expect(checkboxes[2]!.checked).toBe(true);
    });

    it("keeps expanded row details with the same item after local sort", async () => {
        const wrapper = mount(GTable as object, {
            localVue,
            pinia: createTestingPinia({ createSpy: vi.fn }),
            propsData: {
                items: [
                    { id: "1", name: "Pasted Dataset 1", body: "first body" },
                    { id: "2", name: "Pasted Dataset 2", body: "second body" },
                ],
                fields: [{ key: "name", label: "Name", sortable: true }],
                primaryKey: "id",
                sortBy: "name",
                sortDesc: true,
                clickableRows: true,
            },
            scopedSlots: {
                "row-details": rowDetailsSlot,
            },
            attachTo: document.body,
        });

        await wrapper.findAll("tbody tr").wrappers[0]!.trigger("click");
        const rowClick = wrapper.emitted("row-click")?.[0]?.[0] as { toggleDetails: () => void };
        rowClick.toggleDetails();
        await wrapper.vm.$nextTick();
        expect(wrapper.find(".details-body").text()).toBe("second body");

        await wrapper.findAll("thead th").wrappers[0]!.trigger("click");
        await wrapper.vm.$nextTick();

        expect(wrapper.findAll(".details-body").wrappers).toHaveLength(1);
        expect(wrapper.find(".details-body").text()).toBe("second body");
    });
});
