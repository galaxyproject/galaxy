import { registerToastHost, unregisterToastHost, useToast } from "@galaxyproject/galaxy-ui";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";
import VueRouter from "vue-router";

import GToast from "./GToast.vue";

const SELECTORS = {
    G_TOAST: "[data-description='toast message']",
    CLOSE_BUTTON: "[data-description='close toast']",
} as const;

const localVue = getLocalVue();
localVue.use(VueRouter);
const { toasts, addToast, clearToasts } = useToast();

afterEach(() => {
    clearToasts();
    vi.useRealTimers();
});

describe("GToast.vue", () => {
    it("when modal is active, modal triggers toast to render inside main browser window", async () => {
        const host = "modal-toast-host";
        const rootWrapper = mount(GToast as object, { localVue });

        registerToastHost(host);
        const modalWrapper = mount(GToast as object, { propsData: { host }, localVue });
        addToast("Shown above the modal", { duration: 0 });
        await nextTick();

        expect(rootWrapper.find(SELECTORS.G_TOAST).exists()).toBe(false);
        expect(modalWrapper.get(SELECTORS.G_TOAST).text()).toContain("Shown above the modal");

        unregisterToastHost(host);
    });

    it("renders queued toasts with title, message and variant class", async () => {
        const wrapper = mount(GToast as object, { localVue });

        addToast("Something happened", { title: "Heads up", variant: "warning", duration: 0 });
        await nextTick();

        const toast = wrapper.get(SELECTORS.G_TOAST);
        expect(toast.classes()).toContain("g-toast-warning");
        expect(toast.text()).toContain("Heads up");
        expect(toast.text()).toContain("Something happened");
    });

    it("removes a toast when its close button is clicked", async () => {
        const wrapper = mount(GToast as object, { localVue });

        addToast("Dismiss me", { duration: 0 });
        await nextTick();
        expect(wrapper.findAll(SELECTORS.G_TOAST)).toHaveLength(1);

        expect(wrapper.find(SELECTORS.CLOSE_BUTTON).exists()).toBe(true);
        await wrapper.get(SELECTORS.CLOSE_BUTTON).trigger("click");
        expect(toasts.value).toHaveLength(0);
        await nextTick();
        expect(wrapper.get(SELECTORS.G_TOAST).classes()).toContain("g-toast-leave-active");
    });

    it("auto-dismisses a toast after its duration elapses", async () => {
        vi.useFakeTimers();
        const wrapper = mount(GToast as object, { localVue });

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
    ] as const)("%s() raises a %s toast with the default title", async (method, variantClass, defaultTitle) => {
        const wrapper = mount(GToast as object, { localVue });
        const raise = useToast()[method];

        raise("A message");
        await nextTick();

        const toast = wrapper.get(SELECTORS.G_TOAST);
        expect(toast.classes()).toContain(variantClass);
        expect(toast.text()).toContain(defaultTitle);
        expect(toast.text()).toContain("A message");
    });

    it("navigates via the router when a toast with `to` is clicked", async () => {
        const router = new VueRouter({ mode: "abstract", routes: [{ path: "/" }, { path: "/histories/view" }] });
        const wrapper = mount(GToast as object, { localVue, router });

        addToast("Click here to see it.", { to: "/histories/view", duration: 0 });
        await nextTick();

        const toast = wrapper.get(SELECTORS.G_TOAST);
        expect(toast.classes()).toContain("g-toast-clickable");

        await toast.trigger("click");
        expect(router.currentRoute.path).toBe("/histories/view");
    });
});
