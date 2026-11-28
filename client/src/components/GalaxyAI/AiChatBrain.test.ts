import { mount, type VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { defineComponent, h, onBeforeUnmount, onMounted, ref } from "vue";

import { useChatStore } from "@/stores/chatStore";
import { useConfigStore } from "@/stores/configurationStore";
import { useUserStore } from "@/stores/userStore";

import type * as ChatPlugin from "./chatPlugin";

import AiChatBrain from "./AiChatBrain.vue";

const PLUGIN = { href: "/static/plugins/visualizations/fixture/static", entry_point: { attr: { src: "index.js" } } };
const CONFIG = { ai_chat_plugin: "fixture" };

const TAG = "fixture-plugin";
const declared = vi.hoisted(() => ({ webcomponent: true, imported: [] as string[], importing: Promise.resolve() }));

vi.mock("axios", () => ({
    default: {
        get: vi.fn(async () => ({
            data: declared.webcomponent
                ? { ...PLUGIN, entry_point: { attr: { src: "index.js", webcomponent: TAG } } }
                : PLUGIN,
        })),
    },
}));
vi.mock("./chatPlugin", async (original) => ({
    ...(await original<typeof ChatPlugin>()),
    importPlugin: vi.fn(async (url: string) => {
        declared.imported.push(url);
        await declared.importing;
    }),
}));
vi.mock("@/onload/loadConfig", () => ({ getAppRoot: () => "/" }));
vi.mock("@/api/client", () => ({
    GalaxyApi: () => ({ GET: vi.fn(async (path: string) => ({ data: path === "/api/configuration" ? CONFIG : [] })) }),
}));

class FixturePlugin extends HTMLElement {
    static created = 0;
    commands: unknown[] = [];
    incoming: string | null = null;
    connectedCallback() {
        this.incoming = this.getAttribute("data-incoming");
    }
    constructor() {
        super();
        FixturePlugin.created++;
        this.addEventListener("galaxy", (event) => this.commands.push((event as CustomEvent).detail));
    }
    report(detail: object) {
        this.dispatchEvent(
            new CustomEvent("galaxy-visualization", { detail: { from: "galaxy-visualization", ...detail } }),
        );
    }
}
customElements.define(TAG, FixturePlugin);

const Slot = defineComponent({
    setup() {
        const body = ref<HTMLElement | null>(null);
        const store = useChatStore();
        onMounted(() => {
            store.chatSlot = body.value;
        });
        onBeforeUnmount(() => {
            if (store.chatSlot === body.value) {
                store.chatSlot = null;
            }
        });
        return () => h("div", { ref: body });
    },
});

let wrapper: VueWrapper;
const place = ref("center");
const Places = defineComponent({
    setup: () => () =>
        h("div", [
            h(AiChatBrain, { plugin: "fixture" }),
            place.value ? h("div", { class: place.value, key: place.value }, [h(Slot)]) : null,
        ]),
});

beforeEach(async () => {
    declared.imported.length = 0;
    declared.webcomponent = true;
    declared.importing = Promise.resolve();
    FixturePlugin.created = 0;
    setActivePinia(createPinia());
    useConfigStore().setConfiguration(CONFIG);
    useUserStore().currentUser = { id: "u1", email: "u1@example.org" } as never;
    vi.stubGlobal("requestAnimationFrame", () => 0);
    vi.stubGlobal("cancelAnimationFrame", () => {});
    place.value = "";
    wrapper = mount(Places as object, { attachTo: document.body });
    await flushPromises();
});

afterEach(() => {
    wrapper.unmount();
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
});

const element = () => document.querySelector<FixturePlugin>(TAG)!;

describe("the chat plugin's host", () => {
    it("loads nothing until the chat first shows", () => {
        expect(declared.imported).toEqual([]);
        expect(document.querySelector(TAG)).toBeNull();
    });

    it("then imports src and mounts the declared element in the chat's place, configured before it connects", async () => {
        place.value = "center";
        await flushPromises();
        expect(declared.imported).toEqual(["/static/plugins/visualizations/fixture/static/index.js"]);
        expect(document.querySelector("iframe")).toBeNull();
        expect(element().closest(".center")).not.toBeNull();
        expect(JSON.parse(element().incoming!)).toMatchObject({
            root: `${window.location.origin}/`,
            visualization_config: { view: "chat" },
            visualization_plugin: { href: PLUGIN.href },
        });
    });

    it("is ready on its first report, then takes the commands in order", async () => {
        place.value = "center";
        await flushPromises();
        const store = useChatStore();
        store.openChat("a1");
        store.askChat("Count my reads");
        expect(element().commands).toEqual([]);
        element().report({ visualization_saved: true });
        store.askChat("And plot them");
        expect(element().commands).toEqual([
            { from: "galaxy", type: "open", exchange_id: "a1" },
            { from: "galaxy", type: "ask", question: "Count my reads" },
            { from: "galaxy", type: "ask", question: "And plot them" },
        ]);
    });

    it("mounts with a command given before it started, and does not send it again", async () => {
        useChatStore().openChat("a1");
        place.value = "center";
        await flushPromises();
        expect(JSON.parse(element().incoming!).visualization_config).toEqual({ view: "chat", exchange_id: "a1" });
        element().report({ visualization_saved: true });
        expect(element().commands).toEqual([]);
    });

    it("mounts with the first command given while it loads, and sends the rest in order once ready", async () => {
        let imported = () => {};
        declared.importing = new Promise((resolve) => (imported = () => resolve()));
        place.value = "center";
        await flushPromises();
        const store = useChatStore();
        store.openChat("a1");
        store.askChat("Count my reads");
        imported();
        await flushPromises();
        expect(JSON.parse(element().incoming!).visualization_config).toEqual({ view: "chat", exchange_id: "a1" });
        element().report({ visualization_saved: true });
        expect(element().commands).toEqual([{ from: "galaxy", type: "ask", question: "Count my reads" }]);
    });

    it("takes the chat shown and the saved state from its reports", async () => {
        place.value = "center";
        await flushPromises();
        const store = useChatStore();
        element().report({ visualization_saved: false });
        expect(store.unsaved).toBe(true);
        element().report({ visualization_config: { exchange_id: "c1" }, visualization_saved: true });
        expect(store.activeChatId).toBe("c1");
        expect(store.unsaved).toBe(false);
    });

    it("moves the same element between places, keeps it hidden while none shows it, and removes it when the chat goes", async () => {
        place.value = "center";
        await flushPromises();
        const shown = element();
        place.value = "right";
        await flushPromises();
        expect(element()).toBe(shown);
        expect(shown.closest(".right")).not.toBeNull();
        place.value = "";
        await flushPromises();
        expect(shown.isConnected).toBe(true);
        expect(shown.closest(".d-none")).not.toBeNull();
        place.value = "bottom";
        await flushPromises();
        expect(shown.closest(".bottom")).not.toBeNull();
        expect(FixturePlugin.created).toBe(1);
        wrapper.unmount();
        expect(shown.isConnected).toBe(false);
        wrapper = mount(defineComponent({ render: () => h("div") }) as object);
    });

    it("creates nothing when the chat goes while the plugin is still loading", async () => {
        let imported = () => {};
        declared.importing = new Promise((resolve) => (imported = () => resolve()));
        place.value = "center";
        await flushPromises();
        wrapper.unmount();
        imported();
        await flushPromises();
        expect(FixturePlugin.created).toBe(0);
        expect(document.querySelector(TAG)).toBeNull();
        wrapper = mount(defineComponent({ render: () => h("div") }) as object);
    });

    it("fails when the plugin never reports", async () => {
        vi.useFakeTimers();
        place.value = "center";
        await vi.advanceTimersByTimeAsync(30000);
        expect(useChatStore().agentState).toBe("failed");
    });

    it("keeps the commands given after it failed, and sends them in order if it reports late", async () => {
        vi.useFakeTimers();
        place.value = "center";
        await vi.advanceTimersByTimeAsync(30000);
        const store = useChatStore();
        expect(store.agentState).toBe("failed");
        store.openChat("a1");
        store.askChat("Count my reads");
        element().report({ visualization_saved: true });
        expect(store.agentState).toBe("ready");
        expect(element().commands).toEqual([
            { from: "galaxy", type: "open", exchange_id: "a1" },
            { from: "galaxy", type: "ask", question: "Count my reads" },
        ]);
    });

    it("fails, without mounting anything, when the plugin declares no web component", async () => {
        vi.spyOn(console, "error").mockImplementation(() => {});
        declared.webcomponent = false;
        place.value = "center";
        await flushPromises();
        expect(declared.imported).toEqual([]);
        expect(document.querySelector(TAG)).toBeNull();
        expect(useChatStore().agentState).toBe("failed");
    });
});
