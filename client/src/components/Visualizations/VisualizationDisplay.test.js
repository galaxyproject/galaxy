import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { h } from "vue";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import { useUserStore } from "@/stores/userStore";

import VisualizationDisplay from "./VisualizationDisplay.vue";

const guards = { leave: undefined, update: undefined };

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
let stored;
let respond;
let requested;
let pinia;

function deferred() {
    let resolve;
    const promise = new Promise((r) => (resolve = r));
    return { promise, resolve };
}

vi.mock("@/components/Visualizations/VisualizationFrame.vue", () => ({
    default: {
        name: "VisualizationFrame",
        props: ["config", "name", "title", "visualizationId"],
        render: () => h("div"),
    },
}));

const FRAME = { name: "VisualizationFrame" };
const localVue = getLocalVue();

let wrapper;

function savedBy(userId) {
    return { title: "Saved chart", user_id: userId, latest_revision: { config: { a: 1 } } };
}

function viewerFails(message) {
    return HttpResponse.json({ err_msg: message, err_code: 500 }, { status: 500 });
}

function mountDisplay(propsData = { visualization: "example", datasetId: "d1" }) {
    wrapper = mount(VisualizationDisplay, {
        propsData,
        localVue,
        pinia,
        stubs: { LoadingSpan: true },
    });
    return wrapper;
}

async function frameShown() {
    await vi.waitFor(() => expect(wrapper.findComponent(FRAME).exists()).toBe(true));
    return wrapper.findComponent(FRAME);
}

async function openSaved(ownerId) {
    stored = savedBy(ownerId);
    mountDisplay({ visualization: "example", visualizationId: "v1" });
    respond();
    await flushPromises();
    return wrapper;
}

const report = (saved) => wrapper.findComponent(FRAME).vm.$emit("saved", saved);
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
    stored = savedBy(ME);
    viewer = SIGNED_IN;
    viewerResponse = undefined;
    pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
    setActivePinia(pinia);
    const visualizationResponse = deferred();
    respond = visualizationResponse.resolve;
    requested = [];
    server.events.on("request:start", ({ request }) => requested.push(new URL(request.url).pathname));
    server.use(
        http.get("/api/visualizations/{id}", async () => {
            await visualizationResponse.promise;
            return HttpResponse.json(stored);
        }),
        http.get("/api/users/{user_id}", async () => (await viewerResponse) ?? HttpResponse.json(viewer)),
    );
});

afterEach(() => {
    wrapper?.unmount();
    wrapper = undefined;
    server.events.removeAllListeners();
    // happy-dom has no confirm of its own, so the stub has to be taken back off.
    delete window.confirm;
    vi.restoreAllMocks();
});

describe("warning about unsaved work", () => {
    it("warns once the visualization reports an unsaved change, and stops once it saves", async () => {
        mountDisplay();
        await flushPromises();
        expect(unloadIsBlocked()).toBe(false);
        await report(false);
        expect(unloadIsBlocked()).toBe(true);
        await report(true);
        expect(unloadIsBlocked()).toBe(false);
    });

    it("guards a tab or dataset switch, which keeps the same route", async () => {
        mountDisplay();
        await flushPromises();
        await report(false);
        const confirm = refuses();
        expect(decide(guards.update)).toBe(false);
        expect(confirm).toHaveBeenCalled();
    });

    it("guards leaving the route as well", async () => {
        mountDisplay();
        await flushPromises();
        await report(false);
        refuses();
        expect(decide(guards.leave)).toBe(false);
    });

    it("lets a switch through once the visualization is saved", async () => {
        mountDisplay();
        await flushPromises();
        await report(true);
        const confirm = refuses();
        expect(decide(guards.update)).toBe(true);
        expect(confirm).not.toHaveBeenCalled();
    });

    it("leaves nothing listening when it is left while its request is pending", async () => {
        const listening = watchUnloadListeners();
        mountDisplay({ visualization: "example", visualizationId: "v1" });
        expect(listening.size).toBe(1);
        wrapper.unmount();
        respond();
        await flushPromises();
        expect(listening.size).toBe(0);
    });
});

describe("saving a visualization the viewer did not make", () => {
    it("names the saved visualization when the viewer owns it, so saving updates it", async () => {
        await openSaved(ME);
        expect((await frameShown()).props("visualizationId")).toBe("v1");
    });

    it("names nothing when someone else owns it, so saving makes the viewer a copy", async () => {
        await openSaved("someone-else");
        expect((await frameShown()).props("visualizationId")).toBeUndefined();
    });

    it("names nothing for a viewer who is not signed in, who can own nothing", async () => {
        viewer = ANONYMOUS;
        await openSaved(ME);
        expect((await frameShown()).props("visualizationId")).toBeUndefined();
    });

    it("still shows the title and config it was stored under", async () => {
        await openSaved("someone-else");
        const frame = await frameShown();
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
        await openSaved(ME);
        await vi.waitFor(() => expect(requested).toContain("/api/users/current"));
        await flushPromises();
        expect(requested.filter((path) => path.startsWith("/api/histories"))).toEqual([]);
        expect(wrapper.findComponent(FRAME).exists()).toBe(false);
        expect(wrapper.findComponent({ name: "LoadingSpan" }).exists()).toBe(true);
    });

    it("names the saved visualization once the viewer turns out to own it", async () => {
        await openSaved(ME);
        viewerReturns(HttpResponse.json(SIGNED_IN));
        expect((await frameShown()).props("visualizationId")).toBe("v1");
    });

    it("names nothing once the viewer turns out to be someone else", async () => {
        await openSaved("someone-else");
        viewerReturns(HttpResponse.json(SIGNED_IN));
        expect((await frameShown()).props("visualizationId")).toBeUndefined();
    });

    it("shows an error instead of a frame that would save a copy when the viewer cannot be loaded", async () => {
        await openSaved(ME);
        viewerReturns(viewerFails("Network down"));
        await vi.waitFor(() => expect(wrapper.text()).toContain("Network down"));
        expect(wrapper.findComponent(FRAME).exists()).toBe(false);
        expect(wrapper.findComponent({ name: "LoadingSpan" }).exists()).toBe(false);
    });

    it("shows the frame without an error when the viewer loaded but the app's shared load failed later", async () => {
        server.use(
            http.get("/api/histories/count", () => viewerFails("Histories unavailable")),
            http.get("/api/histories", () => viewerFails("Histories unavailable")),
        );
        // The app starts the shared load, with histories, before the view mounts.
        const appLoad = useUserStore().loadUser();
        await openSaved(ME);
        viewerReturns(HttpResponse.json(SIGNED_IN));
        await expect(appLoad).rejects.toThrow();
        expect((await frameShown()).props("visualizationId")).toBe("v1");
        expect(wrapper.text()).not.toContain("Histories unavailable");
    });

    it("shows a dataset preview right away, without waiting on the viewer", async () => {
        mountDisplay();
        await flushPromises();
        expect(wrapper.findComponent(FRAME).exists()).toBe(true);
        expect(requested).not.toContain("/api/users/current");
    });
});

describe("showing a different visualization", () => {
    it("renders a fresh frame when the plugin changes, so the iframe reloads with it", async () => {
        mountDisplay();
        await flushPromises();
        const before = wrapper.findComponent(FRAME).element;
        await wrapper.setProps({ visualization: "another" });
        await flushPromises();
        const frame = wrapper.findComponent(FRAME);
        expect(frame.props("name")).toBe("another");
        expect(frame.element).not.toBe(before);
    });
});
