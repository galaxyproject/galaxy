import { getLocalVue, suppressDebugConsole } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia } from "pinia";
import { describe, expect, it } from "vitest";

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

        const localVue = getLocalVue();
        const pinia = createPinia();
        const wrapper = shallowMount(Index, {
            props: {
                repo: {
                    id: "id",
                    name: "name",
                    owner: "owner",
                    description: "description",
                },
                toolshedUrl: "toolshedUrl",
            },
            global: localVue,
            pinia,
        });
        expect(wrapper.find(".loading-message").text()).toBe("Loading repository details...");
        await flushPromises();
        expect(wrapper.findAll(".alert").length).toBe(0);
    });
});
