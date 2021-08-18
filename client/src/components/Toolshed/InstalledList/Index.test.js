import { mount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import Index from "./Index";

jest.mock("app");

import { getAppRoot } from "onload/loadConfig";
jest.mock("onload/loadConfig");
getAppRoot.mockImplementation(() => "/");

import { Services } from "../services";
jest.mock("../services");

const localVue = getLocalVue();

Services.mockImplementation(() => {
    return {
        async getInstalledRepositories() {
            return [
                {
                    name: "name_0",
                    description: "description_0",
                    tool_shed: "toolshed_1",
                    tool_shed_status: {
                        latest_installable_revision: false,
                    },
                },
                {
                    name: "name_1",
                    description: "description_1",
                    tool_shed: "toolshed_2",
                    tool_shed_status: {
                        latest_installable_revision: true,
                    },
                },
            ];
        },
    };
});

describe("InstalledList", () => {
    it("test installed list", async () => {
        const wrapper = mount(Index, {
            propsData: {
                filter: "",
            },
            stubs: {
                RepositoryDetails: true,
            },
            localVue,
        });
        expect(wrapper.find(".loading-message").text()).toBe("Loading installed repositories...");
        await wrapper.vm.$nextTick();
        expect(wrapper.find(".installed-message").text()).toBe("2 repositories installed on this instance.");
        const names = wrapper.findAll(".name");
        expect(names.length).toBe(2);
        expect(names.at(0).text()).toBe("name_0");
        expect(names.at(1).text()).toBe("name_1");
        const links = wrapper.findAll("a");
        expect(links.length).toBe(3);
        const badge = links.at(1).find(".badge");
        expect(badge.text()).toBe("Newer version available!");
        expect(wrapper.find('th[role="columnheader"][aria-colindex="3"] > div').text()).toBe("Tool Shed");
    });
});
