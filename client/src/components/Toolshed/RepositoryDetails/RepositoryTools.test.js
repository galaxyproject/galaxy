import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

import RepositoryTools from "./RepositoryTools";

describe("RepositoryTools", () => {
    it("test tool version list in repository details", () => {
        const globalConfig = getLocalVue();
        const wrapper = mount(RepositoryTools, {
            props: {
                tools: [
                    {
                        guid: "guid",
                        id: "id",
                        version: "version",
                    },
                ],
            },
            global: globalConfig.global,
        });
        const $el = wrapper.findAll("td");
        const $first = $el[0];
        expect($first.text()).toBe("id");
        const $second = $el[1];
        expect($second.text()).toBe("version");
    });

    it("test collapsing tool version list in repository details", async () => {
        const globalConfig = getLocalVue();
        const wrapper = mount(RepositoryTools, {
            props: {
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
            global: globalConfig.global,
        });
        const $el = wrapper.findAll("tr");
        expect($el.length).toBe(3);
        const $first = $el[0];
        expect($first.find("td:first-child").text()).toBe("id_1");
        expect($first.find("td:last-child").text()).toBe("version_1");
        const $second = $el[1];
        expect($second.find("td:first-child").text()).toBe("id_2");
        expect($second.find("td:last-child").text()).toBe("version_2");
        const $third = $el[2];
        expect($third.find("td:first-child").text()).toBe("Show more");
        expect($third.find("td:last-child").text()).toBe("");
        const $link = wrapper.find("a");
        await $link.trigger("click");

        const $elExpanded = wrapper.findAll("tr");
        expect($elExpanded.length).toBe(4);
        const $thirdExpanded = $elExpanded[3];
        expect($thirdExpanded.find("td:first-child").text()).toBe("id_3");
        expect($thirdExpanded.find("td:last-child").text()).toBe("version_3");
        const $forthExpanded = $elExpanded[0];
        expect($forthExpanded.find("td:first-child").text()).toBe("Show less");
        expect($forthExpanded.find("td:last-child").text()).toBe("");
        const $linkExpanded = wrapper.find("a");
        await $linkExpanded.trigger("click");

        const $elCollapsed = wrapper.findAll("tr");
        expect($elCollapsed.length).toBe(3);
        const $thirdCollapsed = $elCollapsed[2];
        expect($thirdCollapsed.find("td:first-child").text()).toBe("Show more");
        expect($thirdCollapsed.find("td:last-child").text()).toBe("");
    });
});
