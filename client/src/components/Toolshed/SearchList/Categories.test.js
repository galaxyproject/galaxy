import { mount } from "@vue/test-utils";
import Categories from "./Categories";
import { __RewireAPI__ as rewire } from "./Categories";
import Vue from "vue";

describe("Categories", () => {
    beforeEach(() => {
        rewire.__Rewire__(
            "Services",
            class {
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
            }
        );
    });

    it("test categories loading", () => {
        const wrapper = mount(Categories, {
            propsData: {
                loading: true,
                toolshedUrl: "toolshedUrl",
            },
        });
        expect(wrapper.find(".loading-message").text()).toBe("Loading categories...");
    });

    it("test categories table", async () => {
        const wrapper = mount(Categories, {
            propsData: {
                loading: false,
                toolshedUrl: "toolshedUrl",
            },
        });
        await Vue.nextTick();
        const links = wrapper.findAll("a");
        expect(links.length).toBe(2);
        expect(links.at(0).text()).toBe("name_0");
        expect(links.at(1).text()).toBe("name_1");
        const rows = wrapper.findAll("tr");
        expect(rows.length).toBe(3);
        const cells = rows.at(1).findAll("td");
        expect(cells.at(1).text()).toBe("description_0");
        expect(cells.at(2).text()).toBe("repositories_0");
    });
});
