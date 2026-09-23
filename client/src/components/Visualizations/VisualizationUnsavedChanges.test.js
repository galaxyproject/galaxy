import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, describe, expect, it, vi } from "vitest";

import VisualizationDisplay from "./VisualizationDisplay.vue";

const PLUGIN = {
    href: "/static/plugins/visualizations/example/static",
    entry_point: { attr: { src: "index.js", css: "index.css" } },
};

vi.mock("axios", () => ({ default: { get: vi.fn(async () => ({ data: PLUGIN })) } }));
vi.mock("@/onload/loadConfig", () => ({ getAppRoot: () => "/" }));
vi.mock("vue-router/composables", () => ({ onBeforeRouteLeave: vi.fn() }));
vi.mock("@/api", () => ({ GalaxyApi: () => ({ GET: async () => ({ data: null, error: null }) }) }));

let wrapper;

afterEach(() => {
    wrapper?.destroy();
    wrapper = undefined;
    vi.useRealTimers();
});

const unloadIsBlocked = () => !window.dispatchEvent(new Event("beforeunload", { cancelable: true }));

describe("a visualization reporting unsaved work", () => {
    it("warns on unload from the message its own iframe posts, and stops once it saves", async () => {
        wrapper = mount(VisualizationDisplay, {
            propsData: { visualization: "example", datasetId: "d1" },
            stubs: { LoadingSpan: true, BAlert: true },
            attachTo: document.body,
        });
        await flushPromises();
        const frame = wrapper.find("iframe").element;
        expect(frame).toBeDefined();
        vi.useFakeTimers();
        const post = (data) => window.dispatchEvent(new MessageEvent("message", { data, source: frame.contentWindow }));
        expect(unloadIsBlocked()).toBe(false);
        post({
            from: "galaxy-visualization",
            visualization_config: { settings: { a: 1 } },
            visualization_saved: false,
        });
        await vi.advanceTimersByTimeAsync(400);
        expect(unloadIsBlocked()).toBe(true);
        post({ from: "galaxy-visualization", visualization_saved: true });
        await vi.advanceTimersByTimeAsync(400);
        expect(unloadIsBlocked()).toBe(false);
    });
});
