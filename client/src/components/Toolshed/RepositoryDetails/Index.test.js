import { shallowMount, createLocalVue } from "@vue/test-utils";
import Index from "./Index";

jest.mock("app");

import { getAppRoot } from "onload/loadConfig";
jest.mock("onload/loadConfig");
getAppRoot.mockImplementation(() => "/");

import { Services } from "../services";
jest.mock("../services");

Services.mockImplementation(() => {
    return {
        async getRepository(toolshedUrl, repositoryId) {
            expect(toolshedUrl).toBe("toolshedUrl");
            expect(repositoryId).toBe("id");
            return [];
        },
        async getInstalledRepositoriesByName(name, owner) {
            expect(name).toBe("name");
            expect(owner).toBe("owner");
            return [];
        },
    };
});

describe("RepositoryDetails", () => {
    it("test repository details index", async () => {
        const localVue = createLocalVue();
        const wrapper = shallowMount(Index, {
            propsData: {
                repo: {
                    id: "id",
                    name: "name",
                    owner: "owner",
                    description: "description",
                },
                toolshedUrl: "toolshedUrl",
            },
            localVue,
        });
        expect(wrapper.find(".loading-message").text()).toBe("Loading repository details...");
        await localVue.nextTick();
        expect(wrapper.findAll(".alert").length).toBe(0);
        await localVue.nextTick();
        expect(wrapper.findAll(".alert").length).toBe(0);
    });
});
