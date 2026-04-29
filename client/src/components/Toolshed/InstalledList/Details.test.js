import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

import Details from "./Details.vue";

vi.mock("app");
vi.mock("onload/loadConfig", () => ({
    getAppRoot: vi.fn(() => "/"),
}));
vi.mock("../services", () => ({
    Services: class Services {
        async getRepositoryByName(url, name, owner) {
            expect(url).toBe("tool_shed_url");
            expect(name).toBe("name");
            expect(owner).toBe("owner");
            return {};
        }
    },
}));

describe("Details", () => {
    const localVue = getLocalVue();
    it("test repository details loading", async () => {
        const wrapper = shallowMount(Details, {
            props: {
                repo: {
                    tool_shed_url: "tool_shed_url",
                    name: "name",
                    owner: "owner",
                },
            },
            global: localVue,
        });
        expect(wrapper.findAll("loadingspan-stub").length).toBe(1);
        expect(wrapper.find("loadingspan-stub").attributes("message")).toBe("Loading installed repository details");
        expect(wrapper.findAll("repositorydetails-stub").length).toBe(0);
        await nextTick();
        expect(wrapper.findAll("loadingspan-stub").length).toBe(0);
        expect(wrapper.findAll(".alert").length).toBe(0);
        expect(wrapper.findAll("repositorydetails-stub").length).toBe(1);
    });
});
