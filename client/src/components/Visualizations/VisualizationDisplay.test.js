import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import VisualizationDisplay from "./VisualizationDisplay.vue";

const guards = { leave: undefined, update: undefined };

vi.mock("vue-router/composables", () => ({
    onBeforeRouteLeave: (guard) => (guards.leave = guard),
    onBeforeRouteUpdate: (guard) => (guards.update = guard),
}));

const ME = "user-1";
const SIGNED_IN = { id: ME, email: "me@example.org" };

let signedIn;
let stored;
let respond;

vi.mock("@/api", async (importOriginal) => ({
    ...(await importOriginal()),
    GalaxyApi: () => ({ GET: () => new Promise((resolve) => (respond = () => resolve(stored))) }),
}));

vi.mock("@/components/Visualizations/VisualizationFrame.vue", () => ({
    default: {
        name: "VisualizationFrame",
        props: ["config", "name", "title", "visualizationId"],
        render: (h) => h("div"),
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
    let allowed = true;
    guard({}, {}, (proceed) => (allowed = proceed !== false));
    return allowed;
}

beforeEach(() => {
    guards.leave = guards.update = undefined;
    stored = savedBy(ME);
    signedIn = SIGNED_IN;
});

afterEach(() => {
    wrapper?.destroy();
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
        wrapper.destroy();
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
        signedIn = null;
        await openSaved(ME);
        expect(wrapper.findComponent(FRAME).props("visualizationId")).toBeUndefined();
    });

    it("still shows the title and config it was stored under", async () => {
        await openSaved("someone-else");
        expect(wrapper.findComponent(FRAME).props("title")).toBe("Saved chart");
        expect(wrapper.findComponent(FRAME).props("config")).toEqual({ a: 1 });
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
