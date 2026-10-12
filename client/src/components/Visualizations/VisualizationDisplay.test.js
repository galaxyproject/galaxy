import { createTestingPinia } from "@pinia/testing";
import { deferred } from "@tests/vitest/deferred";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { disposePinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, onTestFinished, vi } from "vitest";
import { h } from "vue";

import VisualizationDisplay from "./VisualizationDisplay.vue";

const { guards, getVisualization } = vi.hoisted(() => ({
    guards: { leave: undefined, update: undefined },
    getVisualization: vi.fn(),
}));

vi.mock("vue-router", () => ({
    onBeforeRouteLeave: (guard) => (guards.leave = guard),
    onBeforeRouteUpdate: (guard) => (guards.update = guard),
}));

const ME = "user-1";
const SIGNED_IN = { id: ME, email: "me@example.org" };

vi.mock("@/api", async (importOriginal) => ({
    ...(await importOriginal()),
    GalaxyApi: () => ({ GET: getVisualization }),
}));

vi.mock("@/components/Visualizations/VisualizationFrame.vue", () => ({
    default: {
        name: "VisualizationFrame",
        props: ["config", "name", "title", "visualizationId"],
        render: () => h("div"),
    },
}));

const FRAME = { name: "VisualizationFrame" };
const localVue = getLocalVue();

const originalConfirm = Object.getOwnPropertyDescriptor(window, "confirm");

function savedBy(userId) {
    return { data: { title: "Saved chart", user_id: userId, latest_revision: { config: { a: 1 } } }, error: null };
}

function mountDisplay(
    props = { visualization: "example", datasetId: "d1" },
    { user = SIGNED_IN, response = savedBy(ME) } = {},
) {
    const request = deferred();
    getVisualization.mockReturnValueOnce(request.promise);
    const pinia = createTestingPinia({ createSpy: vi.fn, initialState: { userStore: { currentUser: user } } });
    setActivePinia(pinia);
    onTestFinished(async () => {
        // The wrapper is already unmounted; finish any request before disposing its store.
        request.resolve(response);
        await flushPromises();
        disposePinia(pinia);
    });
    const wrapper = mount(VisualizationDisplay, {
        props,
        global: { ...withPlugins(localVue, pinia), stubs: { LoadingSpan: true } },
    });
    return { wrapper, respond: () => request.resolve(response) };
}

async function openSaved(ownerId, user = SIGNED_IN) {
    const { wrapper, respond } = mountDisplay(
        { visualization: "example", visualizationId: "v1" },
        { user, response: savedBy(ownerId) },
    );
    respond();
    await flushPromises();
    return wrapper;
}

const report = (wrapper, saved) => wrapper.getComponent(FRAME).vm.$emit("saved", saved);
const unloadIsBlocked = () => !window.dispatchEvent(new Event("beforeunload", { cancelable: true }));

function refuses() {
    window.confirm = vi.fn(() => false);
    return window.confirm;
}

function watchUnloadListeners() {
    const listening = new Set();
    const [add, remove] = [window.addEventListener.bind(window), window.removeEventListener.bind(window)];
    vi.spyOn(window, "addEventListener").mockImplementation((type, handler, options) => {
        if (type === "beforeunload") {
            listening.add(handler);
        }
        return add(type, handler, options);
    });
    vi.spyOn(window, "removeEventListener").mockImplementation((type, handler, options) => {
        listening.delete(handler);
        return remove(type, handler, options);
    });
    return listening;
}

function decide(guard) {
    // Vue Router 4 guards signal cancellation via their return value (`false`),
    // not the old `(to, from, next)` callback style.
    const result = guard({}, {});
    return result !== false;
}

beforeEach(() => {
    guards.leave = guards.update = undefined;
    getVisualization.mockReset();
});

afterEach(() => {
    if (originalConfirm) {
        Object.defineProperty(window, "confirm", originalConfirm);
    } else {
        delete window.confirm;
    }
    vi.restoreAllMocks();
});
// Register last so component listeners are removed before their spies are restored.
enableAutoUnmount(afterEach);

describe("warning about unsaved work", () => {
    it("warns once the visualization reports an unsaved change, and stops once it saves", async () => {
        const { wrapper } = mountDisplay();
        await flushPromises();
        expect(unloadIsBlocked()).toBe(false);
        await report(wrapper, false);
        expect(unloadIsBlocked()).toBe(true);
        await report(wrapper, true);
        expect(unloadIsBlocked()).toBe(false);
    });

    it("guards a tab or dataset switch, which keeps the same route", async () => {
        const { wrapper } = mountDisplay();
        await flushPromises();
        await report(wrapper, false);
        const confirm = refuses();
        expect(decide(guards.update)).toBe(false);
        expect(confirm).toHaveBeenCalled();
    });

    it("guards leaving the route as well", async () => {
        const { wrapper } = mountDisplay();
        await flushPromises();
        await report(wrapper, false);
        refuses();
        expect(decide(guards.leave)).toBe(false);
    });

    it("lets a switch through once the visualization is saved", async () => {
        const { wrapper } = mountDisplay();
        await flushPromises();
        await report(wrapper, true);
        const confirm = refuses();
        expect(decide(guards.update)).toBe(true);
        expect(confirm).not.toHaveBeenCalled();
    });

    it("leaves nothing listening when it is left while its request is pending", async () => {
        const listening = watchUnloadListeners();
        const { wrapper, respond } = mountDisplay({ visualization: "example", visualizationId: "v1" });
        expect(listening.size).toBe(1);
        wrapper.unmount();
        respond();
        await flushPromises();
        expect(listening.size).toBe(0);
    });
});

describe("saving a visualization the viewer did not make", () => {
    it("names the saved visualization when the viewer owns it, so saving updates it", async () => {
        const wrapper = await openSaved(ME);
        expect(wrapper.getComponent(FRAME).props("visualizationId")).toBe("v1");
    });

    it("names nothing when someone else owns it, so saving makes the viewer a copy", async () => {
        const wrapper = await openSaved("someone-else");
        expect(wrapper.getComponent(FRAME).props("visualizationId")).toBeUndefined();
    });

    it("names nothing for a viewer who is not signed in, who can own nothing", async () => {
        const wrapper = await openSaved(ME, null);
        expect(wrapper.getComponent(FRAME).props("visualizationId")).toBeUndefined();
    });

    it("still shows the title and config it was stored under", async () => {
        const wrapper = await openSaved("someone-else");
        expect(wrapper.getComponent(FRAME).props("title")).toBe("Saved chart");
        expect(wrapper.getComponent(FRAME).props("config")).toEqual({ a: 1 });
    });
});

describe("showing a different visualization", () => {
    it("renders a fresh frame when the plugin changes, so the iframe reloads with it", async () => {
        const { wrapper } = mountDisplay();
        await flushPromises();
        const before = wrapper.getComponent(FRAME).element;
        await wrapper.setProps({ visualization: "another" });
        await flushPromises();
        const frame = wrapper.getComponent(FRAME);
        expect(frame.props("name")).toBe("another");
        expect(frame.element).not.toBe(before);
    });
});
