import { liveRegionKey } from "@galaxyproject/galaxy-ui";
import { getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount, type VueWrapper } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { defineComponent, h, inject, nextTick } from "vue";

import GAlert from "./GAlert.vue";

const localVue = getLocalVue();

const LiveRegionProbe = defineComponent({
    setup() {
        const insideLiveRegion = inject(liveRegionKey, null);
        return () => h("span", { "data-live-region": String(insideLiveRegion) });
    },
});
const SELECTORS = {
    ALERT: ".alert",
    CLOSE_BUTTON: "button.close",
};

function mountAlert(props: Record<string, unknown> = {}, options: Record<string, unknown> = {}) {
    return mount(GAlert, { global: localVue, props, ...options });
}

function isShown(wrapper: VueWrapper) {
    return wrapper.find(SELECTORS.ALERT).exists();
}

function countdownValues(wrapper: VueWrapper) {
    return wrapper.emitted("dismiss-count-down")?.map(([count]) => count);
}

enableAutoUnmount(afterEach);

describe("GAlert", () => {
    beforeEach(() => {
        vi.useFakeTimers();
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it("self-dismisses when closed", async () => {
        const wrapper = mountAlert({ dismissible: true }, { slots: { default: "Dismiss me" } });

        expect(isShown(wrapper)).toBe(true);

        await wrapper.find(SELECTORS.CLOSE_BUTTON).trigger("click");

        expect(isShown(wrapper)).toBe(false);
        expect(wrapper.emitted("dismissed")).toHaveLength(1);
        expect(wrapper.emitted("input")?.[0]).toEqual([false]);
        expect(wrapper.emitted("update:show")?.[0]).toEqual([false]);
    });

    it("uses default v-model value before the show default", async () => {
        const wrapper = mountAlert({ value: false });

        expect(isShown(wrapper)).toBe(false);

        await wrapper.setProps({ value: true });

        expect(isShown(wrapper)).toBe(true);
    });

    it("counts down numeric show values", async () => {
        const wrapper = mountAlert({ show: 2 });

        expect(isShown(wrapper)).toBe(true);
        expect(countdownValues(wrapper)).toEqual([2]);

        vi.advanceTimersByTime(1000);
        await nextTick();

        expect(isShown(wrapper)).toBe(true);
        expect(countdownValues(wrapper)).toEqual([2, 1]);

        vi.advanceTimersByTime(1000);
        await nextTick();

        expect(isShown(wrapper)).toBe(false);
        expect(countdownValues(wrapper)).toEqual([2, 1, 0]);
        expect(wrapper.emitted("dismissed")).toHaveLength(1);
    });

    it.each([
        ["danger", "alert"],
        ["warning", "alert"],
        ["info", "status"],
        ["success", "status"],
    ])("renders %s alerts with role=%s and no conflicting aria-live", (variant, role) => {
        const alert = mountAlert({ variant }).find(SELECTORS.ALERT);

        expect(alert.attributes("role")).toBe(role);
        expect(alert.attributes("aria-live")).toBeUndefined();
    });

    it("lets call sites override the role", () => {
        const wrapper = mountAlert({ variant: "danger" }, { attrs: { role: "status" } });

        expect(wrapper.find(SELECTORS.ALERT).attributes("role")).toBe("status");
    });

    it("tells its content that it sits inside a live region", () => {
        const wrapper = mount(GAlert, { global: localVue, slots: { default: () => h(LiveRegionProbe) } });
        expect(wrapper.find("[data-live-region]").attributes("data-live-region")).toBe("true");
    });

    it.each(["none", "presentation"])("does not claim a live region when the call site sets role=%s", (role) => {
        const wrapper = mount(GAlert, {
            global: localVue,
            attrs: { role },
            slots: { default: () => h(LiveRegionProbe) },
        });
        expect(wrapper.find(".alert").attributes("role")).toBe(role);
        expect(wrapper.find("[data-live-region]").attributes("data-live-region")).toBe("false");
    });
});
