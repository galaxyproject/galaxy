import Vue from "vue";
import { mount } from "@vue/test-utils";
import RepositoryTools from "./RepositoryTools";

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
        });
        const $el = wrapper.findAll("td");
        const $first = $el.at(0);
        expect($first.text()).to.equal("id");
        const $second = $el.at(1);
        expect($second.text()).to.equal("version");
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
        expect($el.length).to.equal(3);
        const $first = $el.at(0);
        expect($first.find("td:first-child").text()).to.equal("id_1");
        expect($first.find("td:last-child").text()).to.equal("version_1");
        const $second = $el.at(1);
        expect($second.find("td:first-child").text()).to.equal("id_2");
        expect($second.find("td:last-child").text()).to.equal("version_2");
        const $third = $el.at(2);
        expect($third.find("td:first-child").text()).to.equal("Show more");
        expect($third.find("td:last-child").text()).to.equal("");
        const $link = wrapper.find("a");
        $link.trigger("click");
        await Vue.nextTick();

        const $elExpanded = wrapper.findAll("tr");
        expect($elExpanded.length).to.equal(4);
        const $thirdExpanded = $elExpanded.at(3);
        expect($thirdExpanded.find("td:first-child").text()).to.equal("id_3");
        expect($thirdExpanded.find("td:last-child").text()).to.equal("version_3");
        const $forthExpanded = $elExpanded.at(0);
        expect($forthExpanded.find("td:first-child").text()).to.equal("Show less");
        expect($forthExpanded.find("td:last-child").text()).to.equal("");
        const $linkExpanded = wrapper.find("a");
        $linkExpanded.trigger("click");
        await Vue.nextTick();

        const $elCollapsed = wrapper.findAll("tr");
        expect($elCollapsed.length).to.equal(3);
        const $thirdCollapsed = $elCollapsed.at(2);
        expect($thirdCollapsed.find("td:first-child").text()).to.equal("Show more");
        expect($thirdCollapsed.find("td:last-child").text()).to.equal("");
    });
});
