import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import ListHeader from "./ListHeader.vue";

const localVue = getLocalVue();

describe("ListHeader.vue", () => {
    it("keeps the column chooser header inside a named group of the menu", () => {
        const wrapper = mount(ListHeader as object, {
            localVue,
            pinia: createTestingPinia({ createSpy: vi.fn }),
            propsData: {
                listId: "datasets",
                columnOptions: [
                    { key: "name", label: "Name" },
                    { key: "size", label: "Size" },
                ],
                visibleColumns: ["name"],
            },
        });

        expect(wrapper.get(".dropdown-toggle").attributes("aria-label")).toBe("Columns");
        const group = wrapper.get("[role='menu'] > [role='group']");
        expect(group.attributes("aria-label")).toBe("Show/Hide Columns");
        const header = group.get(".dropdown-header");
        expect(header.attributes("role")).toBe("presentation");
        expect(header.find("button").exists()).toBe(true);
    });
});
