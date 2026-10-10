import { createTestingPinia } from "@pinia/testing";
import { getFakeRegisteredUser } from "@tests/test-data";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { setupMockConfig } from "@tests/vitest/mockConfig";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { RegisteredUser } from "@/api";

import QuotaMeter from "./QuotaMeter.vue";

const SELECTORS = {
    USAGE: ".quota-progress > span",
    PROGRESS_BAR: ".quota-progress .progress-bar",
};

function quotaUser(overrides: Partial<RegisteredUser> = {}) {
    return getFakeRegisteredUser({ quota: "100 MB", total_disk_usage: 5120, quota_percent: 50, ...overrides });
}

async function mountQuotaMeter({ enableQuotas, user }: { enableQuotas: boolean; user: RegisteredUser | null }) {
    setupMockConfig({ enable_quotas: enableQuotas });
    const pinia = createTestingPinia({ createSpy: vi.fn, initialState: { userStore: { currentUser: user } } });
    const wrapper = mount(QuotaMeter as object, { global: withPlugins(getLocalVue(), pinia) });
    await flushPromises();
    return wrapper;
}

enableAutoUnmount(afterEach);

describe("QuotaMeter.vue", () => {
    it("shows the percentage of the quota in use", async () => {
        const wrapper = await mountQuotaMeter({ enableQuotas: true, user: quotaUser() });

        expect(wrapper.find(SELECTORS.USAGE).text()).toBe("Using 50% of 100 MB");
    });

    it.each([
        { quotaPercent: 30, variant: "bg-success" },
        { quotaPercent: 80, variant: "bg-warning" },
        { quotaPercent: 95, variant: "bg-danger" },
    ])("colors the bar $variant at $quotaPercent% of the quota", async ({ quotaPercent, variant }) => {
        const wrapper = await mountQuotaMeter({ enableQuotas: true, user: quotaUser({ quota_percent: quotaPercent }) });

        expect(wrapper.find(SELECTORS.PROGRESS_BAR).classes()).toContain(variant);
    });

    it("titles the meter with the storage details for a registered user", async () => {
        const wrapper = await mountQuotaMeter({ enableQuotas: true, user: quotaUser() });

        expect(wrapper.attributes("title")).toBe("Storage and Usage Details");
    });

    it("shows total usage when quotas are disabled", async () => {
        const wrapper = await mountQuotaMeter({ enableQuotas: false, user: quotaUser({ total_disk_usage: 7000 }) });

        expect(wrapper.find(SELECTORS.USAGE).text()).toBe("Using 7 KB");
    });

    it("shows total usage for an unlimited quota", async () => {
        const user = quotaUser({ total_disk_usage: 21000, quota: "unlimited" });
        const wrapper = await mountQuotaMeter({ enableQuotas: true, user });

        expect(wrapper.find(SELECTORS.USAGE).text()).toBe("Using 21 KB");
    });

    it("shows no usage before the user has loaded", async () => {
        const wrapper = await mountQuotaMeter({ enableQuotas: false, user: null });

        expect(wrapper.find(SELECTORS.USAGE).text()).toBe("Using 0 b");
        expect(wrapper.find(SELECTORS.PROGRESS_BAR).attributes("aria-valuenow")).toBe("0");
    });
});
