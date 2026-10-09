import { getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import Repositories from "./Repositories.vue";

const { getRepositories } = vi.hoisted(() => ({ getRepositories: vi.fn() }));

vi.mock("app");
vi.mock("../services", () => ({
    Services: class Services {
        getRepositories = getRepositories;
    },
}));

enableAutoUnmount(afterEach);

function mountRepositories() {
    return mount(Repositories, {
        props: { query: "toolname", scrolled: false, toolshedUrl: "toolshedUrl" },
        global: getLocalVue(),
    });
}

describe("Repositories", () => {
    beforeEach(() => {
        getRepositories.mockReset().mockResolvedValue([
            {
                name: "name_0",
                owner: "owner_0",
                last_updated: "last_updated_0",
                times_downloaded: "times_downloaded_0",
            },
            {
                name: "name_1",
                owner: "owner_1",
                last_updated: "last_updated_1",
                times_downloaded: "times_downloaded_1",
            },
        ]);
    });

    it("replaces the loading message with matching repository links", async () => {
        const wrapper = mountRepositories();
        expect(wrapper.find(".loading-message").text()).toBe("Loading repositories...");

        await flushPromises();

        expect(wrapper.findAll("a").map((link) => link.text())).toEqual(["name_0", "name_1"]);
        expect(getRepositories).toHaveBeenCalledExactlyOnceWith({
            tool_shed_url: "toolshedUrl",
            q: "toolname",
            page: 1,
            page_size: 50,
        });
    });

    it("shows no matching repositories when the search returns no results", async () => {
        getRepositories.mockResolvedValueOnce([]);
        const wrapper = mountRepositories();
        await flushPromises();
        expect(wrapper.find(".unavailable-message").text()).toBe("No matching repositories found.");
        expect(wrapper.findAll("a")).toHaveLength(0);
    });
});
