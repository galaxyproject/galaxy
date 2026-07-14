import { expectConfigurationRequest, getLocalVue } from "@tests/vitest/helpers";
import { setupMockConfig } from "@tests/vitest/mockConfig";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import { useUserStore } from "@/stores/userStore";

import ToolCard from "./ToolCard.vue";

const { server, http } = useServerMock();

vi.mock("@/api/schema");

vi.mock("@/composables/userLocalStorageFromHashedId", async () => {
    const { ref } = await import("vue");
    return {
        useUserLocalStorageFromHashId: (_key, initialValue) => ref(initialValue),
    };
});

const config = { enable_tool_source_display: false };
setupMockConfig(config);

const localVue = getLocalVue();

describe("ToolCard", () => {
    let wrapper;
    let userStore;

    beforeEach(async () => {
        // some child component must be bypassing useConfig - so we need to explicitly
        // stup the API endpoint also. If you can drop this without request problems in log,
        // this hack can be removed.
        server.use(
            expectConfigurationRequest(http, {}),
            http.untyped.get("/api/webhooks", () => {
                return HttpResponse.json([]);
            }),
        );

        const pinia = createPinia();

        wrapper = mount(ToolCard, {
            propsData: {
                id: "identifier",
                version: "version",
                title: "title",
                description: "description",
                sustainVersion: false,
                options: {
                    id: "options.id",
                    name: "options.name",
                    version: "options.version",
                    versions: [],
                    sharable_url: "options.sharable_url",
                    help: "options.help",
                    help_format: "restructuredtext",
                    citations: false,
                },
                messageText: "messageText",
                messageVariant: "warning",
                disabled: false,
            },
            localVue,
            pinia,
        });
        userStore = useUserStore();
        userStore.currentUser = {
            id: "user.id",
            email: "user.email",
            is_admin: true,
            preferences: {},
        };
        await flushPromises();
    });

    it("shows props", async () => {
        const title = wrapper.find("h1");
        expect(title.text()).toBe("title");

        const description = wrapper.find("span[itemprop='description']");
        expect(description.text()).toBe("description");

        const dropdownHeader = wrapper.find(".tool-dropdown");
        expect(dropdownHeader.attributes("title")).toBe("Options");

        const dropdownItems = wrapper.findAll(".dropdown-item");
        expect(dropdownItems.length).toBe(5);

        const backdrop = wrapper.findAll(".portlet-backdrop");
        expect(backdrop.length).toBe(0);

        await wrapper.setProps({ disabled: true });
        const backdropActive = wrapper.findAll(".portlet-backdrop");
        expect(backdropActive.length).toBe(1);
        await flushPromises();
    });

    it("shows newer version badge for older lineage versions", async () => {
        await wrapper.setProps({
            version: "1.0",
            options: {
                ...wrapper.props("options"),
                version: "1.0",
                versions: ["1.0", "2.0"],
            },
        });

        expect(wrapper.find("[data-description='newer tool version']").text()).toBe("Newer version available");
    });

    it("does not show newer version badge for the latest lineage version", async () => {
        await wrapper.setProps({
            version: "2.0",
            options: {
                ...wrapper.props("options"),
                version: "2.0",
                versions: ["1.0", "2.0"],
            },
        });

        expect(wrapper.find("[data-description='newer tool version']").exists()).toBe(false);
    });

    it("does not show newer version badge for a single version", async () => {
        await wrapper.setProps({
            version: "1.0",
            options: {
                ...wrapper.props("options"),
                version: "1.0",
                versions: ["1.0"],
            },
        });

        expect(wrapper.find("[data-description='newer tool version']").exists()).toBe(false);
    });
});
