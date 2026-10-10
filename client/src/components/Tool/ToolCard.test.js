import { createTestingPinia } from "@pinia/testing";
import { getFakeRegisteredUser } from "@tests/test-data";
import { createTestRouter, expectConfigurationRequest, getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { setupMockConfig } from "@tests/vitest/mockConfig";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

import ToolCard from "./ToolCard.vue";

const { server, http } = useServerMock();

vi.mock("@/composables/userLocalStorageFromHashedId", async () => {
    const { ref } = await import("vue");
    return {
        useUserLocalStorageFromHashId: (_key, initialValue) => ref(initialValue),
    };
});

setupMockConfig({ enable_tool_source_display: false });

const SELECTORS = {
    TITLE: "h1",
    DESCRIPTION: "span[itemprop='description']",
    OPTIONS_DROPDOWN: ".tool-dropdown",
    OPTION: ".dropdown-item",
    BACKDROP: ".portlet-backdrop",
    NEWER_VERSION_BADGE: "[data-description='newer tool version']",
};

const ADMIN_USER = getFakeRegisteredUser({ is_admin: true });

const TOOL_OPTIONS = {
    id: "options.id",
    name: "options.name",
    version: "options.version",
    versions: [],
    sharable_url: "options.sharable_url",
    help: "options.help",
    help_format: "restructuredtext",
    citations: false,
};

async function mountToolCard({ version = "version", options = {} } = {}) {
    const pinia = createTestingPinia({ createSpy: vi.fn, initialState: { userStore: { currentUser: ADMIN_USER } } });
    const router = createTestRouter();
    const wrapper = mount(ToolCard, {
        props: {
            id: "identifier",
            version,
            title: "title",
            description: "description",
            sustainVersion: false,
            options: { ...TOOL_OPTIONS, ...options },
            messageText: "messageText",
            messageVariant: "warning",
            disabled: false,
        },
        global: withPlugins(getLocalVue(), pinia, router),
    });
    await flushPromises();
    return { wrapper, router };
}

enableAutoUnmount(afterEach);

describe("ToolCard", () => {
    beforeEach(() => {
        server.use(
            // configurationStore's setup calls loadConfig() before @pinia/testing swaps its actions for spies
            expectConfigurationRequest(http, {}),
            http.untyped.get("/api/webhooks", () => HttpResponse.json([])),
        );
    });

    it("shows the tool's title and description", async () => {
        const { wrapper } = await mountToolCard();

        expect(wrapper.find(SELECTORS.TITLE).text()).toBe("title");
        expect(wrapper.find(SELECTORS.DESCRIPTION).text()).toBe("description");
    });

    it("offers an admin five tool options", async () => {
        const { wrapper } = await mountToolCard();

        expect(wrapper.find(SELECTORS.OPTIONS_DROPDOWN).attributes("title")).toBe("Options");
        expect(wrapper.findAll(SELECTORS.OPTION)).toHaveLength(5);
    });

    it("covers the card with a backdrop while disabled", async () => {
        const { wrapper } = await mountToolCard();
        expect(wrapper.findAll(SELECTORS.BACKDROP)).toHaveLength(0);

        await wrapper.setProps({ disabled: true });

        expect(wrapper.findAll(SELECTORS.BACKDROP)).toHaveLength(1);
    });

    it("shows a newer version badge that navigates to the latest version", async () => {
        const { wrapper, router } = await mountToolCard({
            version: "1.0",
            options: { version: "1.0", versions: ["1.0", "2.0"] },
        });

        const badge = wrapper.find(SELECTORS.NEWER_VERSION_BADGE);
        expect(badge.text()).toBe("Newer version available");

        await badge.trigger("click");
        await flushPromises();

        expect(router.currentRoute.value.fullPath).toBe("/?tool_id=identifier&version=latest");
    });

    it.each([
        { scenario: "the latest version in its lineage", version: "2.0", versions: ["1.0", "2.0"] },
        { scenario: "a single-version tool", version: "1.0", versions: ["1.0"] },
    ])("shows no newer version badge for $scenario", async ({ version, versions }) => {
        const { wrapper } = await mountToolCard({ version, options: { version, versions } });

        expect(wrapper.find(SELECTORS.NEWER_VERSION_BADGE).exists()).toBe(false);
    });
});
