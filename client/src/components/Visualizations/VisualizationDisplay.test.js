import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { h } from "vue";

import { useUserStore } from "@/stores/userStore";

import VisualizationDisplay from "./VisualizationDisplay.vue";

const guards = { leave: undefined, update: undefined };

vi.mock("vue-router", () => ({
    onBeforeRouteLeave: (guard) => (guards.leave = guard),
    onBeforeRouteUpdate: (guard) => (guards.update = guard),
}));

const ME = "user-1";
const SIGNED_IN = { id: ME, email: "me@example.org" };
const ANONYMOUS = { isAnonymous: true };

let signedIn;
let stored;
let respond;
let loadingViewer;

vi.mock("@/api", async (importOriginal) => ({
    ...(await importOriginal()),
    GalaxyApi: () => ({ GET: () => new Promise((resolve) => (respond = () => resolve(stored))) }),
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

let wrapper;

function savedBy(userId) {
    return { data: { title: "Saved chart", user_id: userId, latest_revision: { config: { a: 1 } } }, error: null };
}

function mountDisplay(propsData = { visualization: "example", datasetId: "d1" }) {
    const pinia = createTestingPinia({ createSpy: vi.fn, initialState: { userStore: { currentUser: signedIn } } });
    setActivePinia(pinia);
    const userStore = useUserStore();
    userStore.loadUser.mockResolvedValue(undefined);
    if (loadingViewer) {
        // Stands in for the store's own load, which sets the user once the request returns.
        // The load is shared with the app's, whose history load can still fail after that.
        userStore.loadUser.mockImplementation(() =>
            loadingViewer.then((historiesError) => {
                userStore.currentUser = SIGNED_IN;
                if (historiesError) {
                    throw historiesError;
                }
            }),
        );
    }
    wrapper = mount(VisualizationDisplay, {
        propsData,
        localVue,
        pinia,
        stubs: { LoadingSpan: true },
    });
    return wrapper;
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
    signedIn = SIGNED_IN;
    loadingViewer = undefined;
});

afterEach(() => {
    wrapper?.unmount();
    wrapper = undefined;
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
        expect(wrapper.findComponent(FRAME).props("visualizationId")).toBe("v1");
    });

    it("names nothing when someone else owns it, so saving makes the viewer a copy", async () => {
        await openSaved("someone-else");
        expect(wrapper.findComponent(FRAME).props("visualizationId")).toBeUndefined();
    });

    it("names nothing for a viewer who is not signed in, who can own nothing", async () => {
        signedIn = ANONYMOUS;
        await openSaved(ME);
        expect(wrapper.findComponent(FRAME).props("visualizationId")).toBeUndefined();
    });

    it("still shows the title and config it was stored under", async () => {
        await openSaved("someone-else");
        expect(wrapper.findComponent(FRAME).props("title")).toBe("Saved chart");
        expect(wrapper.findComponent(FRAME).props("config")).toEqual({ a: 1 });
    });
});

describe("opening a saved visualization before the viewer is known", () => {
    let viewerLoaded;
    let viewerFailed;

    beforeEach(() => {
        signedIn = null;
        loadingViewer = new Promise((resolve, reject) => {
            viewerLoaded = resolve;
            viewerFailed = reject;
        });
    });

    it("loads the viewer without their histories and holds the frame back until then", async () => {
        await openSaved(ME);
        expect(useUserStore().loadUser).toHaveBeenCalledWith(false);
        expect(wrapper.findComponent(FRAME).exists()).toBe(false);
        expect(wrapper.findComponent({ name: "LoadingSpan" }).exists()).toBe(true);
    });

    it("names the saved visualization once the viewer turns out to own it", async () => {
        await openSaved(ME);
        viewerLoaded();
        await flushPromises();
        expect(wrapper.findComponent(FRAME).props("visualizationId")).toBe("v1");
    });

    it("names nothing once the viewer turns out to be someone else", async () => {
        await openSaved("someone-else");
        viewerLoaded();
        await flushPromises();
        expect(wrapper.findComponent(FRAME).exists()).toBe(true);
        expect(wrapper.findComponent(FRAME).props("visualizationId")).toBeUndefined();
    });

    it("shows an error instead of a frame that would save a copy when the viewer cannot be loaded", async () => {
        await openSaved(ME);
        viewerFailed(new Error("Network down"));
        await flushPromises();
        expect(wrapper.findComponent(FRAME).exists()).toBe(false);
        expect(wrapper.findComponent({ name: "LoadingSpan" }).exists()).toBe(false);
        expect(wrapper.text()).toContain("Failed to load the current user.");
    });

    it("shows the frame without an error when the viewer loaded but the shared load failed later", async () => {
        await openSaved(ME);
        viewerLoaded(new Error("Histories unavailable"));
        await flushPromises();
        expect(wrapper.findComponent(FRAME).props("visualizationId")).toBe("v1");
        expect(wrapper.text()).not.toContain("Histories unavailable");
    });

    it("leaves the viewer alone for a dataset preview, which has nothing to save in place", async () => {
        mountDisplay();
        await flushPromises();
        expect(useUserStore().loadUser).not.toHaveBeenCalled();
        expect(wrapper.findComponent(FRAME).exists()).toBe(true);
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
