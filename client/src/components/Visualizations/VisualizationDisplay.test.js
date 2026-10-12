import { createTestingPinia } from "@pinia/testing";
import { deferred } from "@tests/vitest/deferred";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { disposePinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, onTestFinished, vi } from "vitest";
import { h } from "vue";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import { useUserStore } from "@/stores/userStore";

import VisualizationDisplay from "./VisualizationDisplay.vue";

const { guards } = vi.hoisted(() => ({
    guards: { leave: undefined, update: undefined },
}));

vi.mock("vue-router", () => ({
    onBeforeRouteLeave: (guard) => (guards.leave = guard),
    onBeforeRouteUpdate: (guard) => (guards.update = guard),
}));

const ME = "user-1";
const SIGNED_IN = { id: ME, email: "me@example.org", preferences: {} };
const ANONYMOUS = { total_disk_usage: 0 };

const { server, http } = useServerMock();

let viewer;
let viewerResponse;
let requested;
let pinia;

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
    return { title: "Saved chart", user_id: userId, latest_revision: { config: { a: 1 } } };
}

function viewerFails(message) {
    return HttpResponse.json({ err_msg: message, err_code: 500 }, { status: 500 });
}

/** Mounts the display; its saved-visualization request answers `response` once `respond` is called. */
function mountDisplay(props = { visualization: "example", datasetId: "d1" }, { response = savedBy(ME) } = {}) {
    const request = deferred();
    server.use(
        http.get("/api/visualizations/{id}", async () => {
            await request.promise;
            return HttpResponse.json(response);
        }),
    );
    onTestFinished(async () => {
        // The wrapper is already unmounted; finish any request before disposing its store.
        request.resolve();
        await flushPromises();
        disposePinia(pinia);
    });
    const wrapper = mount(VisualizationDisplay, {
        props,
        global: { ...withPlugins(localVue, pinia), stubs: { LoadingSpan: true } },
    });
    return { wrapper, respond: () => request.resolve() };
}

async function frameShown(wrapper) {
    await vi.waitFor(() => expect(wrapper.findComponent(FRAME).exists()).toBe(true));
    return wrapper.getComponent(FRAME);
}

async function openSaved(ownerId) {
    const { wrapper, respond } = mountDisplay(
        { visualization: "example", visualizationId: "v1" },
        { response: savedBy(ownerId) },
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
    viewer = SIGNED_IN;
    viewerResponse = undefined;
    // Created before mounting, since a test may start the app's user load first.
    pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
    setActivePinia(pinia);
    requested = [];
    server.events.on("request:start", ({ request }) => requested.push(new URL(request.url).pathname));
    server.use(http.get("/api/users/{user_id}", async () => (await viewerResponse) ?? HttpResponse.json(viewer)));
});

afterEach(() => {
    server.events.removeAllListeners();
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
        expect((await frameShown(wrapper)).props("visualizationId")).toBe("v1");
    });

    it("names nothing when someone else owns it, so saving makes the viewer a copy", async () => {
        const wrapper = await openSaved("someone-else");
        expect((await frameShown(wrapper)).props("visualizationId")).toBeUndefined();
    });

    it("names nothing for a viewer who is not signed in, who can own nothing", async () => {
        viewer = ANONYMOUS;
        const wrapper = await openSaved(ME);
        expect((await frameShown(wrapper)).props("visualizationId")).toBeUndefined();
    });

    it("still shows the title and config it was stored under", async () => {
        const wrapper = await openSaved("someone-else");
        const frame = await frameShown(wrapper);
        expect(frame.props("title")).toBe("Saved chart");
        expect(frame.props("config")).toEqual({ a: 1 });
    });
});

describe("opening a saved visualization before the viewer is known", () => {
    let viewerReturns;

    beforeEach(() => {
        const pending = deferred();
        viewerResponse = pending.promise;
        viewerReturns = pending.resolve;
    });

    it("loads the viewer without their histories and holds the frame back until then", async () => {
        const wrapper = await openSaved(ME);
        await vi.waitFor(() => expect(requested).toContain("/api/users/current"));
        await flushPromises();
        expect(requested.filter((path) => path.startsWith("/api/histories"))).toEqual([]);
        expect(wrapper.findComponent(FRAME).exists()).toBe(false);
        expect(wrapper.findComponent({ name: "LoadingSpan" }).exists()).toBe(true);
    });

    it("names the saved visualization once the viewer turns out to own it", async () => {
        const wrapper = await openSaved(ME);
        viewerReturns(HttpResponse.json(SIGNED_IN));
        expect((await frameShown(wrapper)).props("visualizationId")).toBe("v1");
    });

    it("names nothing once the viewer turns out to be someone else", async () => {
        const wrapper = await openSaved("someone-else");
        viewerReturns(HttpResponse.json(SIGNED_IN));
        expect((await frameShown(wrapper)).props("visualizationId")).toBeUndefined();
    });

    it("shows an error instead of a frame that would save a copy when the viewer cannot be loaded", async () => {
        const wrapper = await openSaved(ME);
        viewerReturns(viewerFails("Network down"));
        await vi.waitFor(() => expect(wrapper.text()).toContain("Network down"));
        expect(wrapper.findComponent(FRAME).exists()).toBe(false);
        expect(wrapper.findComponent({ name: "LoadingSpan" }).exists()).toBe(false);
    });

    it("recovers once the app's Retry loads the viewer after all", async () => {
        const wrapper = await openSaved(ME);
        viewerReturns(viewerFails("Network down"));
        await vi.waitFor(() => expect(wrapper.text()).toContain("Network down"));
        viewerResponse = undefined;
        await useUserStore().loadUser(false);
        expect((await frameShown(wrapper)).props("visualizationId")).toBe("v1");
        expect(wrapper.text()).not.toContain("Network down");
    });

    it("names nothing when the app's Retry loads a viewer who does not own it", async () => {
        const wrapper = await openSaved("someone-else");
        viewerReturns(viewerFails("Network down"));
        await vi.waitFor(() => expect(wrapper.text()).toContain("Network down"));
        viewerResponse = undefined;
        await useUserStore().loadUser(false);
        expect((await frameShown(wrapper)).props("visualizationId")).toBeUndefined();
        expect(wrapper.text()).not.toContain("Network down");
    });

    it("shows the frame without an error when the viewer loaded but the app's shared load failed later", async () => {
        server.use(
            http.get("/api/histories/count", () => viewerFails("Histories unavailable")),
            http.get("/api/histories", () => viewerFails("Histories unavailable")),
        );
        // The app starts the shared load, with histories, before the view mounts.
        const appLoad = useUserStore().loadUser();
        const wrapper = await openSaved(ME);
        viewerReturns(HttpResponse.json(SIGNED_IN));
        await expect(appLoad).rejects.toThrow();
        expect((await frameShown(wrapper)).props("visualizationId")).toBe("v1");
        expect(wrapper.text()).not.toContain("Histories unavailable");
    });

    it("shows a dataset preview right away, without waiting on the viewer", async () => {
        const { wrapper } = mountDisplay();
        await flushPromises();
        expect(wrapper.findComponent(FRAME).exists()).toBe(true);
        expect(requested).not.toContain("/api/users/current");
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
