import { createLocalVue, shallowMount } from "@vue/test-utils";
import { getAppRoot } from "onload/loadConfig";

import { Services } from "../services";
import Index from "./Index";

jest.mock("app");
jest.mock("onload/loadConfig");
getAppRoot.mockImplementation(() => "/");
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
