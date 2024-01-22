import { createLocalVue, shallowMount } from "@vue/test-utils";
import { getAppRoot } from "onload/loadConfig";

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
    const localVue = createLocalVue();
    it("test repository details loading", async () => {
        const wrapper = shallowMount(Details, {
            propsData: {
                repo: {
                    tool_shed_url: "tool_shed_url",
                    name: "name",
                    owner: "owner",
                },
            },
            localVue,
        });
        expect(wrapper.findAll("loadingspan-stub").length).toBe(1);
        expect(wrapper.find("loadingspan-stub").attributes("message")).toBe("Loading installed repository details");
        expect(wrapper.findAll("repositorydetails-stub").length).toBe(0);
        await localVue.nextTick();
        expect(wrapper.findAll("loadingspan-stub").length).toBe(0);
        expect(wrapper.findAll(".alert").length).toBe(0);
        expect(wrapper.findAll("repositorydetails-stub").length).toBe(1);
    });
});
