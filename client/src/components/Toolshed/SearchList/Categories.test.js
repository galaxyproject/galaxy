import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

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
        localVue = getLocalVue();
    });

    it("test categories loading", () => {
        const wrapper = mount(Categories, {
            props: {
                loading: true,
                toolshedUrl: "toolshedUrl",
            },
            global: localVue,
        });
        expect(wrapper.find("loadingspan-stub").attributes("message")).toBe("Loading categories");
    });

    it("test categories table", async () => {
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

        expect(links.at(0).text()).toContain("name_0");
        expect(links.at(1).text()).toContain("name_1");

        const rows = wrapper.findAll("tr");
        expect(rows.length).toBe(3);
        const cells = rows.at(1).findAll("td");
        expect(cells.at(1).text()).toBe("description_0");
        expect(cells.at(2).text()).toBe("repositories_0");
    });
});
