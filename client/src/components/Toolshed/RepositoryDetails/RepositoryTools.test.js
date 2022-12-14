import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import RepositoryTools from "./RepositoryTools";

const localVue = getLocalVue();

describe("RepositoryTools", () => {
    it("test tool version list in repository details", () => {
        const wrapper = mount(RepositoryTools, {
            propsData: {
                tools: [
                    {
                        guid: "guid",
                        id: "id",
                        version: "version",
                    },
                ],
            },
            localVue,
        });
        const $el = wrapper.findAll("td");
        const $first = $el.at(0);
        expect($first.text()).toBe("id");
        const $second = $el.at(1);
        expect($second.text()).toBe("version");
    });

    it("test collapsing tool version list in repository details", async () => {
        const wrapper = mount(RepositoryTools, {
            propsData: {
                tools: [
                    {
                        guid: "guid_1",
                        id: "id_1",
                        version: "version_1",
                    },
                    {
                        guid: "guid_2",
                        id: "id_2",
                        version: "version_2",
                    },
                    {
                        guid: "guid_3",
                        id: "id_3",
                        version: "version_3",
                    },
                ],
            },
        });
        const $el = wrapper.findAll("tr");
        expect($el.length).toBe(3);
        const $first = $el.at(0);
        expect($first.find("td:first-child").text()).toBe("id_1");
        expect($first.find("td:last-child").text()).toBe("version_1");
        const $second = $el.at(1);
        expect($second.find("td:first-child").text()).toBe("id_2");
        expect($second.find("td:last-child").text()).toBe("version_2");
        const $third = $el.at(2);
        expect($third.find("td:first-child").text()).toBe("Show more");
        expect($third.find("td:last-child").text()).toBe("");
        const $link = wrapper.find("a");
        await $link.trigger("click");

        const $elExpanded = wrapper.findAll("tr");
        expect($elExpanded.length).toBe(4);
        const $thirdExpanded = $elExpanded.at(3);
        expect($thirdExpanded.find("td:first-child").text()).toBe("id_3");
        expect($thirdExpanded.find("td:last-child").text()).toBe("version_3");
        const $forthExpanded = $elExpanded.at(0);
        expect($forthExpanded.find("td:first-child").text()).toBe("Show less");
        expect($forthExpanded.find("td:last-child").text()).toBe("");
        const $linkExpanded = wrapper.find("a");
        await $linkExpanded.trigger("click");

        const $elCollapsed = wrapper.findAll("tr");
        expect($elCollapsed.length).toBe(3);
        const $thirdCollapsed = $elCollapsed.at(2);
        expect($thirdCollapsed.find("td:first-child").text()).toBe("Show more");
        expect($thirdCollapsed.find("td:last-child").text()).toBe("");
    });
});
