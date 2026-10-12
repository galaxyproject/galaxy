import { getLocalVue, nth } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

import Categories from "./Categories.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

vi.mock("../services", () => ({
    Services: class Services {
        async getCategories() {
            return [
                {
                    name: "name_0",
                    description: "description_0",
                    repositories: "repositories_0",
                },
                {
                    name: "name_1",
                    description: "description_1",
                    repositories: "repositories_1",
                },
            ];
        }
    },
}));

describe("Categories", () => {
    const localVue = getLocalVue();
    enableAutoUnmount(afterEach);

    it("shows the loading message while categories load", () => {
        const wrapper = mount(Categories, {
            props: {
                loading: true,
                toolshedUrl: "toolshedUrl",
            },
            global: localVue,
        });
        // LoadingSpan isn't stubbed, so check the real component's props directly.
        expect(wrapper.getComponent(LoadingSpan).props("message")).toBe("Loading categories");
    });

    it("renders category names, descriptions and repository counts in order", async () => {
        const wrapper = mount(Categories, {
            props: {
                loading: false,
                toolshedUrl: "toolshedUrl",
            },
            global: localVue,
        });
        await nextTick();
        const links = wrapper.findAll("a");
        expect(links.length).toBe(2);

        expect(nth(links, 0).text()).toContain("name_0");
        expect(nth(links, 1).text()).toContain("name_1");

        const rows = wrapper.findAll("tr");
        expect(rows.length).toBe(3);
        const cells = nth(rows, 1).findAll("td");
        expect(nth(cells, 1).text()).toBe("description_0");
        expect(nth(cells, 2).text()).toBe("repositories_0");
    });
});
