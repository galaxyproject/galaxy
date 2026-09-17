import { createLocalVue, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import Categories from "./Categories.vue";
import GLink from "@/components/BaseComponents/GLink.vue";

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
    let localVue;
    beforeEach(() => {
        localVue = createLocalVue();
    });

    it("test categories loading", () => {
        const wrapper = mount(Categories, {
            propsData: {
                loading: true,
                toolshedUrl: "toolshedUrl",
            },
            localVue,
            stubs: {
                LoadingSpan: true,
            },
        });
        expect(wrapper.find("loadingspan-stub").attributes("message")).toBe("Loading categories");
    });

    it("test categories table", async () => {
        const wrapper = mount(Categories, {
            propsData: {
                loading: false,
                toolshedUrl: "toolshedUrl",
            },
            localVue,
            stubs: {
                GLink,
            },
        });
        await localVue.nextTick();
        const links = wrapper.findAllComponents(GLink);
        expect(links.length).toBe(2);

        expect(links.at(0).text()).toContain("name_0");
        expect(links.at(1).text()).toContain("name_1");

        const rows = wrapper.findAll("tr");
        expect(rows.length).toBe(3);
        const cells = rows.at(1).findAll("td");
        expect(cells.at(1).text()).toBe("description_0");
        expect(cells.at(2).text()).toBe("repositories_0");
    });
});
