import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import Index from "./Index.vue";
import GLink from "@/components/BaseComponents/GLink.vue";

vi.mock("app");
vi.mock("onload/loadConfig", () => ({
    getAppRoot: vi.fn(() => "/"),
}));
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

describe("InstalledList", () => {
    it("test installed list", async () => {
        const localVue = getLocalVue();
        const wrapper = mount(Index, {
            props: {
                filter: "",
            },
            stubs: {
                RepositoryDetails: true,
                GLink,
                LoadingSpan: true,
            },
            global: localVue,
        });
        expect(wrapper.find("loadingspan-stub").attributes("message")).toBe("Loading installed repositories");
        await wrapper.vm.$nextTick();
        expect(wrapper.find(".installed-message").text()).toBe("2 repositories installed on this instance.");
        const names = wrapper.findAll(".name");
        expect(names.length).toBe(2);
        expect(names.at(0).text()).toBe("name_0");
        expect(names.at(1).text()).toBe("name_1");
        const links = wrapper.findAllComponents(GLink);
        expect(links.length).toBe(3);
        const badge = links.at(1).find(".badge");
        expect(badge.text()).toBe("Newer version available!");
        expect(wrapper.vm.fields.some((field) => field.key === "tool_shed")).toBe(true);
    });
});
