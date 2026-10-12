import { registerToastHost, unregisterToastHost, useToast } from "@galaxyproject/galaxy-ui";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";
import type { Router } from "vue-router";

import { createMemoryRouter } from "./test-utils";

import GToast from "./GToast.vue";

const SELECTORS = {
    G_TOAST: "[data-description='toast message']",
    CLOSE_BUTTON: "[data-description='close toast']",
} as const;

const localVue = getLocalVue();
const { toasts, addToast, clearToasts } = useToast();

// Every mounted host reads the same queue; unmount before clearing singleton
// state or restoring timers so a failed assertion cannot leak a host or toast.
const mountedWrappers: Array<{ unmount: () => void }> = [];
const registeredHosts = new Set<string>();

function registerHost(host: string) {
    registerToastHost(host);
    registeredHosts.add(host);
}

function mountGToast({
    host,
    router,
    realTransitions = false,
}: { host?: string; router?: Router; realTransitions?: boolean } = {}) {
    const global = router ? withPlugins(localVue, router) : localVue;
    const wrapper = mount(GToast, {
        props: { host },
        global: {
            ...global,
            // Keep real transitions only when checking their leave classes.
            stubs: { ...global.stubs, TransitionGroup: !realTransitions },
        },
    });
    mountedWrappers.push(wrapper);
    return wrapper;
}

afterEach(() => {
    mountedWrappers.splice(0).forEach((wrapper) => wrapper.unmount());
    registeredHosts.forEach(unregisterToastHost);
    registeredHosts.clear();
    clearToasts();
    if (vi.isFakeTimers()) {
        vi.clearAllTimers();
    }
    vi.useRealTimers();
});

describe("GToast.vue", () => {
    it("renders only in the modal host while it is active, then returns to the root host", async () => {
        const host = "modal-toast-host";
        const rootWrapper = mountGToast();

        registerHost(host);
        const modalWrapper = mountGToast({ host });
        addToast("Shown above the modal", { duration: 0 });
        await nextTick();

        expect(rootWrapper.find(SELECTORS.G_TOAST).exists()).toBe(false);
        expect(modalWrapper.get(SELECTORS.G_TOAST).text()).toContain("Shown above the modal");

        unregisterToastHost(host);
        await nextTick();

        expect(modalWrapper.find(SELECTORS.G_TOAST).exists()).toBe(false);
        expect(rootWrapper.get(SELECTORS.G_TOAST).text()).toContain("Shown above the modal");
    });

    it("renders queued toasts with title, message and variant class", async () => {
        const wrapper = mountGToast();

        addToast("Something happened", { title: "Heads up", variant: "warning", duration: 0 });
        await nextTick();

        const toast = wrapper.get(SELECTORS.G_TOAST);
        expect(toast.classes()).toContain("g-toast-warning");
        expect(toast.text()).toContain("Heads up");
        expect(toast.text()).toContain("Something happened");
    });

    it("removes a toast when its close button is clicked", async () => {
        vi.useFakeTimers();
        const wrapper = mountGToast({ realTransitions: true });

        addToast("Dismiss me", { duration: 0 });
        await nextTick();
        expect(wrapper.findAll(SELECTORS.G_TOAST)).toHaveLength(1);

        expect(wrapper.find(SELECTORS.CLOSE_BUTTON).exists()).toBe(true);
        await wrapper.get(SELECTORS.CLOSE_BUTTON).trigger("click");
        expect(toasts.value).toHaveLength(0);
        await nextTick();
        expect(wrapper.get(SELECTORS.G_TOAST).classes()).toContain("g-toast-leave-active");
    });

    it("gives the icon-only close button an accessible name", async () => {
        const wrapper = mountGToast();

        addToast("Dismiss me", { duration: 0 });
        await nextTick();

        expect(wrapper.get(SELECTORS.CLOSE_BUTTON).attributes("aria-label")).toBe("Dismiss notification");
    });

    it("auto-dismisses a toast after its duration elapses", async () => {
        vi.useFakeTimers();
        const wrapper = mountGToast({ realTransitions: true });

        addToast("Temporary", { duration: 1000 });
        await nextTick();
        expect(wrapper.findAll(SELECTORS.G_TOAST)).toHaveLength(1);

        vi.advanceTimersByTime(1000);
        expect(toasts.value).toHaveLength(0);
        await nextTick();
        expect(wrapper.get(SELECTORS.G_TOAST).classes()).toContain("g-toast-leave-active");
    });

    it.each([
        ["success", "g-toast-success", "Success"],
        ["info", "g-toast-info", "Info"],
        ["warning", "g-toast-warning", "Warning"],
        ["error", "g-toast-danger", "Error"],
    ] as const)("%s() renders the %s variant and its default title", async (method, variantClass, defaultTitle) => {
        const wrapper = mountGToast();
        const raise = useToast()[method];

        raise("A message");
        await nextTick();

        const toast = wrapper.get(SELECTORS.G_TOAST);
        expect(toast.classes()).toContain(variantClass);
        expect(toast.text()).toContain(defaultTitle);
        expect(toast.text()).toContain("A message");
    });

    it("navigates via the router when a toast with `to` is clicked", async () => {
        const router = createMemoryRouter({ paths: ["/", "/histories/view"] });
        await router.push("/");
        const wrapper = mountGToast({ router });

        addToast("Click here to see it.", { to: "/histories/view", duration: 0 });
        await nextTick();

        const toast = wrapper.get(SELECTORS.G_TOAST);
        expect(toast.classes()).toContain("g-toast-clickable");

        await toast.trigger("click");
        await flushPromises();
        expect(router.currentRoute.value.path).toBe("/histories/view");
    });
});
