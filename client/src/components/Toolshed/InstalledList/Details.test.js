import { getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, describe, expect, it, vi } from "vitest";

import Details from "./Details.vue";

const { getRepositoryByName } = vi.hoisted(() => ({ getRepositoryByName: vi.fn().mockResolvedValue({}) }));

vi.mock("app");
vi.mock("onload/loadConfig", () => ({
    getAppRoot: vi.fn(() => "/"),
}));
vi.mock("../services", () => ({
    Services: class Services {
        getRepositoryByName = getRepositoryByName;
    },
}));

enableAutoUnmount(afterEach);

describe("Details", () => {
    it("replaces the loading indicator with installed repository details", async () => {
        const wrapper = shallowMount(Details, {
            props: {
                repo: {
                    tool_shed_url: "tool_shed_url",
                    name: "name",
                    owner: "owner",
                },
            },
            global: getLocalVue(),
        });
        expect(wrapper.findAll("loading-span-stub")).toHaveLength(1);
        expect(wrapper.find("loading-span-stub").attributes("message")).toBe("Loading installed repository details");
        expect(wrapper.find("repository-details-stub").exists()).toBe(false);

        await flushPromises();

        expect(wrapper.find("loading-span-stub").exists()).toBe(false);
        expect(wrapper.find(".alert").exists()).toBe(false);
        expect(wrapper.findAll("repository-details-stub")).toHaveLength(1);
        expect(getRepositoryByName).toHaveBeenCalledExactlyOnceWith("tool_shed_url", "name", "owner");
    });
});
