import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { getAppRoot } from "onload/loadConfig";
import { getLocalVue } from "tests/jest/helpers";

import { Services } from "../services";
import Details from "./Details";

jest.mock("app");
jest.mock("onload/loadConfig");
getAppRoot.mockImplementation(() => "/");
jest.mock("../services");

Services.mockImplementation(() => {
    return {
        async getRepositoryByName(url, name, owner) {
            expect(url).toBe("tool_shed_url");
            expect(name).toBe("name");
            expect(owner).toBe("owner");
            return {};
        },
    };
});

describe("Details", () => {
    const globalConfig = getLocalVue();
    it("test repository details loading", async () => {
        const wrapper = shallowMount(Details, {
            props: {
                repo: {
                    tool_shed_url: "tool_shed_url",
                    name: "name",
                    owner: "owner",
                },
            },
            global: globalConfig.global,
        });
        // Since the mock resolves immediately, the loading state is already false
        await flushPromises();
        await wrapper.vm.$nextTick();
        
        // After loading completes, verify the component shows repository details
        expect(wrapper.vm.loading).toBe(false);
        expect(wrapper.findAll(".alert").length).toBe(0);
        const repoDetails = wrapper.findComponent({ name: "RepositoryDetails" });
        expect(repoDetails.exists()).toBe(true);
        expect(repoDetails.props("repo")).toEqual({});
        expect(repoDetails.props("toolshedUrl")).toBe("tool_shed_url");
    });
});
