import { shallowMount } from "@vue/test-utils";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import { getAppRoot } from "onload/loadConfig";
import { createPinia } from "pinia";
import { getLocalVue } from "tests/jest/helpers";

import { mockFetcher } from "@/api/schema/__mocks__";

import { Services } from "../services";
import Index from "./Index";

jest.mock("app");
jest.mock("onload/loadConfig");
getAppRoot.mockImplementation(() => "/");
jest.mock("../services");
jest.mock("@/api/schema");

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
        const axiosMock = new MockAdapter(axios);
        axiosMock.onGet("api/tool_panel?in_panel=true&view=default").reply(200, {});
        mockFetcher.path("/api/configuration").method("get").mock({ data: {} });
        const localVue = getLocalVue();
        const pinia = createPinia();
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
            pinia,
        });
        expect(wrapper.find(".loading-message").text()).toBe("Loading repository details...");
        await localVue.nextTick();
        expect(wrapper.findAll(".alert").length).toBe(0);
        await localVue.nextTick();
        expect(wrapper.findAll(".alert").length).toBe(0);
    });
});
