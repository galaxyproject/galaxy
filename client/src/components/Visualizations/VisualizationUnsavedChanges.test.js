import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { afterEach, describe, expect, it, vi } from "vitest";

import VisualizationDisplay from "./VisualizationDisplay.vue";

const PLUGIN = {
    href: "/static/plugins/visualizations/example/static",
    entry_point: { attr: { src: "index.js", css: "index.css" } },
};

vi.mock("axios", () => ({ default: { get: vi.fn(async () => ({ data: PLUGIN })) } }));
vi.mock("@/onload/loadConfig", () => ({ getAppRoot: () => "/" }));
vi.mock("vue-router/composables", () => ({ onBeforeRouteLeave: vi.fn(), onBeforeRouteUpdate: vi.fn() }));
vi.mock("@/api", async (importOriginal) => ({
    ...(await importOriginal()),
    GalaxyApi: () => ({ GET: async () => ({ data: null, error: null }) }),
}));

const localVue = getLocalVue();

let wrapper;

afterEach(() => {
    wrapper?.destroy();
    wrapper = undefined;
    vi.useRealTimers();
});

const unloadIsBlocked = () => !window.dispatchEvent(new Event("beforeunload", { cancelable: true }));

describe("a visualization reporting unsaved work", () => {
    async function openVisualization() {
        const pinia = createTestingPinia({ createSpy: vi.fn });
        setActivePinia(pinia);
        wrapper = mount(VisualizationDisplay, {
            propsData: { visualization: "example", datasetId: "d1" },
            localVue,
            pinia,
            stubs: { LoadingSpan: true, BAlert: true },
            attachTo: document.body,
        });
        await flushPromises();
        const frame = wrapper.find("iframe").element;
        return (data) => window.dispatchEvent(new MessageEvent("message", { data, source: frame.contentWindow }));
    }

    it("warns on unload from the message its own iframe posts, and stops once it saves", async () => {
        const post = await openVisualization();
        expect(unloadIsBlocked()).toBe(false);
        post({
            from: "galaxy-visualization",
            visualization_config: { settings: { a: 1 } },
            visualization_saved: false,
        });
        await flushPromises();
        expect(unloadIsBlocked()).toBe(true);
        post({ from: "galaxy-visualization", visualization_saved: true });
        await flushPromises();
        expect(unloadIsBlocked()).toBe(false);
    });

    it("warns without waiting out the debounce a config change is held for", async () => {
        const post = await openVisualization();
        vi.useFakeTimers();
        post({
            from: "galaxy-visualization",
            visualization_config: { settings: { a: 1 } },
            visualization_saved: false,
        });
        await vi.advanceTimersByTimeAsync(50);
        expect(unloadIsBlocked()).toBe(true);
    });
});
