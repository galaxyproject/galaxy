import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { resetMockConfig, setMockConfig } from "@/composables/__mocks__/config";
import { useAdminExtensionsStore } from "@/stores/adminExtensionsStore";

import AdminPanel from "./AdminPanel.vue";

vi.mock("@/composables/config");

vi.mock("@/onload/loadConfig", async (importOriginal) => {
    const actual = await importOriginal();
    return { ...actual, getAppRoot: () => "/galaxy/" };
});

vi.mock("vue-router", async (importOriginal) => {
    const actual = await importOriginal();
    return { ...actual, useRoute: vi.fn(() => ({})) };
});

enableAutoUnmount(afterEach);
beforeEach(() => resetMockConfig());

function createTarget(props = {}, extensions = []) {
    const pinia = createTestingPinia({ stubActions: true, createSpy: vi.fn });
    const store = useAdminExtensionsStore(pinia);
    store.extensions = extensions;
    store.loaded = true;
    return mount(AdminPanel, {
        props,
        global: { ...withPlugins(getLocalVue(true), pinia), stubs: { RouterLink: true } },
    });
}

describe("AdminPanel", () => {
    it.each([
        {
            scenario: "shows Tool Shed installation when Tool Shed URLs are configured",
            config: { tool_shed_urls: ["toolshed_url"] },
            link: "#admin-link-toolshed",
            visible: true,
        },
        {
            scenario: "hides Tool Shed installation when Tool Shed URLs are absent",
            config: { tool_shed_urls: undefined },
            link: "#admin-link-toolshed",
            visible: false,
        },
        {
            scenario: "shows quotas when quotas are enabled",
            config: { enable_quotas: true },
            link: "#admin-link-quotas",
            visible: true,
        },
        {
            scenario: "hides quotas when quotas are not configured",
            config: { enable_quotas: undefined },
            link: "#admin-link-quotas",
            visible: false,
        },
    ])("$scenario", ({ config, link, visible }) => {
        setMockConfig({ ...config, version_major: "1.0.1" });
        const wrapper = createTarget();

        expect(wrapper.find(link).exists()).toBe(visible);
    });

    it("appends a section per extension with framed and external links", async () => {
        const extensions = [
            {
                id: "anvil",
                section: "AnVIL",
                items: [
                    { id: "monitor", type: "link", title: "Cluster Monitor", url: "/monitor", target: "iframe" },
                    { id: "docs", type: "link", title: "Docs", url: "https://example.org", target: "new_tab" },
                    { id: "welcome", type: "link", title: "Welcome", url: "/static/welcome.html", target: "new_tab" },
                ],
            },
        ];
        const wrapper = createTarget({}, extensions);
        await flushPromises();

        const titles = wrapper.findAll(".unified-panel-divider-text").map((w) => w.text());
        expect(titles[titles.length - 1]).toBe("AnVIL");

        const framed = wrapper.find("#admin-link-ext-anvil-monitor");
        expect(framed.exists()).toBe(true);
        expect(framed.attributes("to")).toBe("/admin/extensions/anvil/monitor");

        const external = wrapper.find("a#admin-link-ext-anvil-docs");
        expect(external.exists()).toBe(true);
        expect(external.attributes("href")).toBe("https://example.org");
        expect(external.attributes("target")).toBe("_blank");
        expect(external.text()).toBe("Docs");

        // A Galaxy-relative URL gets the configured URL prefix, like framed links do through CenterFrame.
        const local = wrapper.find("a#admin-link-ext-anvil-welcome");
        expect(local.attributes("href")).toBe("/galaxy/static/welcome.html");
    });
});
