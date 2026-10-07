import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import GAlert from "./GAlert.vue";

const localVue = getLocalVue();

describe("GAlert", () => {
    beforeEach(() => {
        vi.useFakeTimers();
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it("self-dismisses when closed", async () => {
        const wrapper = mount(GAlert, {
            global: localVue,
            props: {
                dismissible: true,
            },
            slots: {
                default: "Dismiss me",
            },
        });

        expect(wrapper.find(".alert").exists()).toBe(true);

        await wrapper.find("button.close").trigger("click");

        expect(wrapper.find(".alert").exists()).toBe(false);
        expect(wrapper.emitted("dismissed")).toHaveLength(1);
        expect(wrapper.emitted("input")?.[0]).toEqual([false]);
        expect(wrapper.emitted("update:show")?.[0]).toEqual([false]);
    });

    it("uses default v-model value before the show default", async () => {
        const wrapper = mount(GAlert, {
            global: localVue,
            props: {
                value: false,
            },
        });

        expect(wrapper.find(".alert").exists()).toBe(false);

        await wrapper.setProps({ value: true });

        expect(wrapper.find(".alert").exists()).toBe(true);
    });

    it("counts down numeric show values", async () => {
        const wrapper = mount(GAlert, {
            global: localVue,
            props: {
                show: 2,
            },
        });

        expect(wrapper.find(".alert").exists()).toBe(true);
        expect(wrapper.emitted("dismiss-count-down")?.map(([count]) => count)).toEqual([2]);

        vi.advanceTimersByTime(1000);
        await wrapper.vm.$nextTick();

        expect(wrapper.find(".alert").exists()).toBe(true);
        expect(wrapper.emitted("dismiss-count-down")?.map(([count]) => count)).toEqual([2, 1]);

        vi.advanceTimersByTime(1000);
        await wrapper.vm.$nextTick();

        expect(wrapper.find(".alert").exists()).toBe(false);
        expect(wrapper.emitted("dismiss-count-down")?.map(([count]) => count)).toEqual([2, 1, 0]);
        expect(wrapper.emitted("dismissed")).toHaveLength(1);
    });

    it.each([
        ["danger", "alert"],
        ["warning", "alert"],
        ["info", "status"],
        ["success", "status"],
    ])("renders %s alerts with role=%s and no conflicting aria-live", (variant, role) => {
        const wrapper = mount(GAlert, { global: localVue, props: { variant } });
        const alert = wrapper.find(".alert");
        expect(alert.attributes("role")).toBe(role);
        expect(alert.attributes("aria-live")).toBeUndefined();
    });

    it("lets call sites override the role", () => {
        const wrapper = mount(GAlert, {
            global: localVue,
            props: { variant: "danger" },
            attrs: { role: "status" },
        });
        expect(wrapper.find(".alert").attributes("role")).toBe("status");
    });
});
