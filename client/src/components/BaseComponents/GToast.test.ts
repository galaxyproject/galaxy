import { useToast } from "@galaxyproject/galaxy-ui";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

import GToast from "./GToast.vue";

const localVue = getLocalVue();
const { toasts, addToast, clearToasts } = useToast();

afterEach(() => {
    clearToasts();
    vi.useRealTimers();
});

describe("GToast.vue", () => {
    it("renders queued toasts with title, message and variant class", async () => {
        const wrapper = mount(GToast as object, { localVue });

        addToast("Something happened", { title: "Heads up", variant: "warning", duration: 0 });
        await nextTick();

        const toast = wrapper.get(".g-toast");
        expect(toast.classes()).toContain("g-toast-warning");
        expect(toast.text()).toContain("Heads up");
        expect(toast.text()).toContain("Something happened");
    });

    it("removes a toast when its close button is clicked", async () => {
        const wrapper = mount(GToast as object, { localVue });

        addToast("Dismiss me", { duration: 0 });
        await nextTick();
        expect(wrapper.findAll(".g-toast")).toHaveLength(1);

        await wrapper.get(".g-toast-header button").trigger("click");
        expect(toasts.value).toHaveLength(0);
        await nextTick();
        expect(wrapper.get(".g-toast").classes()).toContain("g-toast-leave-active");
    });

    it("auto-dismisses a toast after its duration elapses", async () => {
        vi.useFakeTimers();
        const wrapper = mount(GToast as object, { localVue });

        addToast("Temporary", { duration: 1000 });
        await nextTick();
        expect(wrapper.findAll(".g-toast")).toHaveLength(1);

        vi.advanceTimersByTime(1000);
        expect(toasts.value).toHaveLength(0);
        await nextTick();
        expect(wrapper.get(".g-toast").classes()).toContain("g-toast-leave-active");
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

        const toast = wrapper.get(".g-toast");
        expect(toast.classes()).toContain(variantClass);
        expect(toast.text()).toContain(defaultTitle);
        expect(toast.text()).toContain("A message");
    });
});
