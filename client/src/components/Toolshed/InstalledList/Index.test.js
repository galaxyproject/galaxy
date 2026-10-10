import { getLocalVue, nth } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";

import Index from "./Index.vue";
import GLink from "@/components/BaseComponents/GLink.vue";

vi.mock("../services", () => ({
    Services: class Services {
        async getInstalledRepositories() {
            return [
                {
                    name: "name_0",
                    description: "description_0",
                    tool_shed: "toolshed_1",
                    tool_shed_status: {
                        latest_installable_revision: false,
                    },
                },
                {
                    name: "name_1",
                    description: "description_1",
                    tool_shed: "toolshed_2",
                    tool_shed_status: {
                        latest_installable_revision: true,
                    },
                },
            ];
        }
    },
}));

const SELECTORS = {
    LOADING: "loading-span-stub",
    INSTALLED_MESSAGE: ".installed-message",
    REPOSITORY_NAME: ".name",
    BADGE: ".badge",
    COLUMN_HEADER: "thead th",
};

function mountInstalledList() {
    const localVue = getLocalVue();
    return mount(Index, {
        props: { filter: "" },
        global: {
            ...localVue,
            stubs: { ...localVue.stubs, RepositoryDetails: true, LoadingSpan: true },
        },
    });
}

describe("InstalledList", () => {
    it("shows a loading message until the installed repositories arrive", async () => {
        const wrapper = mountInstalledList();

        expect(wrapper.find(SELECTORS.LOADING).attributes("message")).toBe("Loading installed repositories");

        await flushPromises();

        expect(wrapper.find(SELECTORS.LOADING).exists()).toBe(false);
    });

    it("lists the installed repositories and flags ones with a newer version", async () => {
        const wrapper = mountInstalledList();
        await flushPromises();

        expect(wrapper.find(SELECTORS.INSTALLED_MESSAGE).text()).toBe("2 repositories installed on this instance.");
        const names = wrapper.findAll(SELECTORS.REPOSITORY_NAME);
        expect(names.length).toBe(2);
        expect(nth(names, 0).text()).toBe("name_0");
        expect(nth(names, 1).text()).toBe("name_1");

        // The installation-progress toggle, then one link per repository.
        const links = wrapper.findAllComponents(GLink);
        expect(links.length).toBe(3);
        expect(nth(links, 1).find(SELECTORS.BADGE).text()).toBe("Newer version available!");
        expect(nth(links, 2).find(SELECTORS.BADGE).exists()).toBe(false);
    });

    it("adds a Tool Shed column when repositories come from more than one Tool Shed", async () => {
        const wrapper = mountInstalledList();
        await flushPromises();

        expect(wrapper.findAll(SELECTORS.COLUMN_HEADER).map((th) => th.text())).toContain("Tool Shed");
    });
});
