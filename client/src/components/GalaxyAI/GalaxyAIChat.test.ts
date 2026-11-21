import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { describe, expect, it, vi } from "vitest";

import { useConfigStore } from "@/stores/configurationStore";
import { useUserStore } from "@/stores/userStore";

import GalaxyAIChat from "./GalaxyAIChat.vue";
import PluginChat from "./PluginChat.vue";
import GalaxyAI from "@/components/GalaxyAI.vue";

vi.mock("@/api/client", () => ({ GalaxyApi: () => ({ GET: vi.fn(() => new Promise(() => {})) }) }));

const localVue = getLocalVue();

function mountChat(
    config: Record<string, unknown> | null,
    propsData: Record<string, unknown>,
    user: object | null = { id: "u1", email: "u1@example.org" },
) {
    const pinia = createPinia();
    setActivePinia(pinia);
    if (config) {
        useConfigStore().setConfiguration(config);
    }
    useUserStore().currentUser = user as never;
    return shallowMount(GalaxyAIChat as object, { localVue, pinia, propsData });
}

describe("GalaxyAIChat", () => {
    it("shows the configured plugin in every place", () => {
        for (const source of ["center", "docked", "panel"]) {
            const wrapper = mountChat(
                { ai_chat_plugin: "fixture", llm_api_configured: true },
                { source, exchangeId: "a1", initialQuestion: "Hi" },
            );
            expect(wrapper.findComponent(GalaxyAI).exists()).toBe(false);
            expect(wrapper.findComponent(PluginChat).props()).toEqual({
                source,
                exchangeId: "a1",
                initialQuestion: "Hi",
            });
        }
    });

    it("shows Galaxy's own chat without a plugin", () => {
        const docked = mountChat({ llm_api_configured: true }, { source: "docked", exchangeId: "a1" });
        expect(docked.findComponent(PluginChat).exists()).toBe(false);
        expect(docked.findComponent(GalaxyAI).props()).toMatchObject({ exchangeId: "a1", docked: true, panel: false });
        const center = mountChat(
            { llm_api_configured: true },
            { source: "center", compact: true, initialQuestion: "Hi" },
        );
        expect(center.findComponent(GalaxyAI).props()).toMatchObject({
            initialQuestion: "Hi",
            compact: true,
            docked: false,
            panel: false,
        });
    });

    it("shows nothing until it knows which chat to show", () => {
        for (const wrapper of [
            mountChat(null, { source: "center" }),
            mountChat({ ai_chat_plugin: "fixture" }, { source: "center" }, null),
        ]) {
            expect(wrapper.findComponent(PluginChat).exists()).toBe(false);
            expect(wrapper.findComponent(GalaxyAI).exists()).toBe(false);
        }
    });

    it("shows Galaxy's own chat without waiting for the user when no plugin is configured", () => {
        const wrapper = mountChat({ llm_api_configured: true }, { source: "center" }, null);
        expect(wrapper.findComponent(GalaxyAI).exists()).toBe(true);
    });
});
