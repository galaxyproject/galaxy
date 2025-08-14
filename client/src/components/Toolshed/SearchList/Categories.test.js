import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import { nextTick } from "vue";

import { Services } from "../services";
import Categories from "./Categories";

jest.mock("../services");

Services.mockImplementation(() => {
    return {
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
        },
    };
});

describe("Categories", () => {
    it("test categories loading", () => {
        const globalConfig = getLocalVue();
        const wrapper = mount(Categories, {
            props: {
                loading: true,
                toolshedUrl: "toolshedUrl",
            },
            global: globalConfig.global,
        });
        expect(wrapper.find(".loading-message").text()).toBe("Loading categories...");
    });

    it("test categories table", async () => {
        const globalConfig = getLocalVue();
        const wrapper = mount(Categories, {
            props: {
                loading: false,
                toolshedUrl: "toolshedUrl",
            },
            global: globalConfig.global,
        });
        await nextTick();
        const links = wrapper.findAll("a");
        expect(links.length).toBe(2);
        expect(links[0].text()).toBe("name_0");
        expect(links[1].text()).toBe("name_1");
        const rows = wrapper.findAll("tr");
        expect(rows.length).toBe(3);
        const cells = rows[1].findAll("td");
        expect(cells[1].text()).toBe("description_0");
        expect(cells[2].text()).toBe("repositories_0");
    });
});
