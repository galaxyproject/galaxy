import { getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { resetMockConfig, setMockConfig } from "@/composables/__mocks__/config";

import AdminPanel from "./AdminPanel.vue";

vi.mock("@/composables/config");

enableAutoUnmount(afterEach);
beforeEach(() => resetMockConfig());

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
        const wrapper = mount(AdminPanel, {
            global: { ...getLocalVue(true), stubs: { RouterLink: true } },
        });

        expect(wrapper.find(link).exists()).toBe(visible);
    });
});
