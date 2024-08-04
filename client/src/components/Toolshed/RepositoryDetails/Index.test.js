import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { getAppRoot } from "onload/loadConfig";
import { createPinia } from "pinia";
import { getLocalVue } from "tests/jest/helpers";

import { useServerMock } from "@/api/client/__mocks__";

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

const { server, http } = useServerMock();

describe("RepositoryDetails", () => {
    it("test repository details index", async () => {
        server.use(
            http.get("/api/tool_panels/default", ({ response }) => {
                return response(200).json({});
            }),
            http.get("/api/configuration", ({ response }) => {
                return response(200).json({});
            })
        );

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
        await flushPromises();
        expect(wrapper.findAll(".alert").length).toBe(0);
    });
});
