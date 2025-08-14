import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { getLocalVue, suppressDebugConsole } from "tests/jest/helpers";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

import Index from "./Index.vue";

const { server, http } = useServerMock();

describe("RepositoryDetails", () => {
    suppressDebugConsole(); // we issue a debug warning when a repo has no revisions

    it("test repository details index", async () => {
        server.use(
            http.get("/api/configuration", ({ response }) => {
                return response(200).json({});
            }),

            http.untyped.get("/api/tool_panels/default", () => {
                return HttpResponse.json({});
            }),

            http.untyped.get("api/tool_shed_repositories", () => {
                return HttpResponse.json([]);
            }),

            http.untyped.get("api/tool_shed/request", () => {
                return HttpResponse.json([]);
            }),
        );

        const globalConfig = getLocalVue();
        const pinia = createPinia();
        setActivePinia(pinia);
        const wrapper = shallowMount(Index as any, {
            props: {
                repo: {
                    id: "id",
                    name: "name",
                    owner: "owner",
                    description: "description",
                },
                toolshedUrl: "toolshedUrl",
            },
            global: {
                ...globalConfig.global,
                plugins: [...globalConfig.global.plugins, pinia],
            },
        });
        await wrapper.vm.$nextTick();
        const loadingMessage = wrapper.find(".loading-message");
        if (loadingMessage.exists()) {
            expect(loadingMessage.text()).toBe("Loading repository details...");
        }
        await flushPromises();
        expect(wrapper.findAll(".alert").length).toBe(0);
    });
});
