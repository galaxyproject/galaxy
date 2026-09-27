import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";

import { useConfig } from "@/composables/config";
import { useAdminExtensionsStore } from "@/stores/adminExtensionsStore";

import MountTarget from "./AdminPanel.vue";

const localVue = getLocalVue(true);

vi.mock("@/composables/config", () => ({
    useConfig: vi.fn(() => ({
        config: { value: { enable_quotas: true, tool_shed_urls: ["tool_shed_url"], version_major: "1.0.1" } },
        isConfigLoaded: true,
    })),
}));

vi.mock("vue-router", async (importOriginal) => {
    const actual = await importOriginal();
    return {
        ...actual,
        useRoute: vi.fn(() => ({})),
    };
});

function createTarget(propsData = {}, extensions = []) {
    const pinia = createTestingPinia({ stubActions: true, createSpy: vi.fn });
    const store = useAdminExtensionsStore(pinia);
    store.extensions = extensions;
    store.loaded = true;
    return mount(MountTarget, {
        global: localVue,
        pinia,
        propsData,
        stubs: {
            routerLink: true,
        },
    });
}

describe("AdminPanel", () => {
    it("ensure section visibility with config changes", async () => {
        const options = [
            {
                name: "tool_shed_urls",
                elementId: "#admin-link-toolshed",
                value: ["toolshed_url"],
            },
            {
                name: "enable_quotas",
                elementId: "#admin-link-quotas",
                value: true,
            },
        ];
        for (const available of [true, false]) {
            for (const option of options) {
                const props = {};
                props[option.name] = available ? option.value : undefined;
                useConfig.mockImplementation(() => ({
                    config: { value: { ...props, version_major: "1.0.1" } },
                    isConfigLoaded: true,
                }));
                const wrapper = createTarget();
                expect(wrapper.find(option.elementId).exists()).toBe(available);
            }
        }
    });

    it("shows no extension sections when none are loaded", () => {
        const wrapper = createTarget();
        expect(wrapper.text()).not.toContain("AnVIL");
        expect(wrapper.find("[id^='admin-link-ext-']").exists()).toBe(false);
    });

    it("appends a section per extension with framed and external links", async () => {
        const extensions = [
            {
                id: "anvil",
                section: "AnVIL",
                items: [
                    { id: "monitor", type: "link", title: "Cluster Monitor", url: "/monitor", target: "iframe" },
                    { id: "docs", type: "link", title: "Docs", url: "https://example.org", target: "new_tab" },
                    { id: "batch", type: "form", title: "GCP Batch", inputs: [] },
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

        const form = wrapper.find("#admin-link-ext-anvil-batch");
        expect(form.exists()).toBe(true);
        expect(form.attributes("to")).toBe("/admin/extensions/anvil/batch");
    });
});
