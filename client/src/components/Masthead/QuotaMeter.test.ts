import { createTestingPinia } from "@pinia/testing";
import { getFakeQuotaUsageData, getFakeRegisteredUser } from "@tests/test-data";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { setupMockConfig } from "@tests/vitest/mockConfig";
import { advanceTooltipHoverDelay } from "@tests/vitest/tooltipTestUtils";
import { mount, type VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { RegisteredUser } from "@/api";
import { useServerMock } from "@/api/client/__mocks__";
import { vGTooltip } from "@/directives/vGTooltip";
import { useQuotaUsageStore } from "@/stores/quotaUsageStore";
import { useUserStore } from "@/stores/userStore";
import { DEFAULT_TOOLTIP_HOVER_DELAY_MS } from "@/utils/tooltipTiming";

import QuotaMeter from "./QuotaMeter.vue";

vi.mock("@/api/schema");

// The real tooltip directive, which the test setup replaces with a no-op
const baseLocalVue = getLocalVue();
const localVue = { ...baseLocalVue, directives: { ...baseLocalVue.directives, "g-tooltip": vGTooltip } };
const { server, http } = useServerMock();

const OTHER_SOURCES_HINT = "[data-description='other storage over quota']";
const SOURCE_USAGE = "[data-description='quota source usage']";
const SOURCE_NAME = "[data-description='quota source name']";
const DASHBOARD_BUTTON = "[data-description='storage dashboard button']";

/** Hovers the meter and returns the text of the tooltip it shows, if any. */
async function hoverForTooltip(wrapper: VueWrapper) {
    vi.useFakeTimers();
    try {
        await wrapper.trigger("mouseenter");
        await advanceTooltipHoverDelay(DEFAULT_TOOLTIP_HOVER_DELAY_MS);
    } finally {
        vi.useRealTimers();
    }
    return document.body.querySelector(".g-tooltip-d")?.textContent ?? null;
}

async function createQuotaMeterWrapper(config: any, user: RegisteredUser) {
    setupMockConfig(config);
    const pinia = createTestingPinia({ createSpy: vi.fn });
    const userStore = useUserStore();
    userStore.currentUser = user;
    const wrapper = mount(QuotaMeter as object, {
        global: localVue,
        pinia,
        attachTo: document.body,
    });
    await flushPromises();
    return wrapper;
}

const FAKE_USER = getFakeRegisteredUser({ quota: "100 MB", total_disk_usage: 5120, quota_percent: 50 });

describe("QuotaMeter.vue", () => {
    it("shows a percentage usage", async () => {
        const config = { enable_quotas: true };
        const wrapper = await createQuotaMeterWrapper(config, FAKE_USER);
        expect(wrapper.find(".quota-progress > span").text()).toBe("Using 50% of 100 MB");
    });

    it("changes appearance depending on usage", async () => {
        const config = { enable_quotas: true };
        {
            const user = { ...FAKE_USER, quota_percent: 30 };
            const wrapper = await createQuotaMeterWrapper(config, user);
            expect(wrapper.find(".quota-progress .progress-bar").classes()).toContain("bg-success");
        }
        {
            const user = { ...FAKE_USER, quota_percent: 80 };
            const wrapper = await createQuotaMeterWrapper(config, user);
            expect(wrapper.find(".quota-progress .progress-bar").classes()).toContain("bg-warning");
        }
        {
            const user = { ...FAKE_USER, quota_percent: 95 };
            const wrapper = await createQuotaMeterWrapper(config, user);
            expect(wrapper.find(".quota-progress .progress-bar").classes()).toContain("bg-danger");
        }
    });

    it("shows a tooltip on hover", async () => {
        const wrapper = await createQuotaMeterWrapper({ enable_quotas: true }, FAKE_USER);
        const tooltip = await hoverForTooltip(wrapper);
        wrapper.unmount();

        expect(tooltip).toBe("Storage and Usage Details");
    });

    it("shows total usage when there is no quota", async () => {
        {
            const user = { ...FAKE_USER, total_disk_usage: 7000 };
            const config = { enable_quotas: false };
            const wrapper = await createQuotaMeterWrapper(config, user);
            expect(wrapper.find("span").text()).toBe("Using 7 KB");
        }
        {
            const user = { ...FAKE_USER, total_disk_usage: 21000, quota: "unlimited" };
            const config = { enable_quotas: true };
            const wrapper = await createQuotaMeterWrapper(config, user);
            expect(wrapper.find("span").text()).toBe("Using 21 KB");
        }
    });

    describe("with other storage sources", () => {
        const SOURCE_QUOTA = 1000;

        /** The storages each quota source belongs to: two share ``scratch``, none uses ``archive``. */
        const STORAGES = [
            { object_store_id: "default", name: "Default Storage", quota: { enabled: true } },
            { object_store_id: "scratch", name: "Scratch Storage", quota: { source: "scratch", enabled: true } },
            { object_store_id: "fast_scratch", name: "Fast Scratch", quota: { source: "scratch", enabled: true } },
            { object_store_id: "secure", name: "Secure Storage", quota: { source: "secure", enabled: true } },
        ].map((storage) => ({ ...storage, private: false, badges: [] }));

        let wrapper: VueWrapper;

        afterEach(() => {
            wrapper.unmount();
        });

        /** Mounts the meter with storage sources that each have a quota of ``SOURCE_QUOTA`` bytes. */
        async function mountWithSourceUsages(usageBySource: Record<string, number>, { enableQuotas = true } = {}) {
            server.use(
                http.get("/api/users/{user_id}/usage", ({ response }) => {
                    return response(200).json(
                        Object.entries(usageBySource).map(([label, usage]) =>
                            getFakeQuotaUsageData(label, usage, SOURCE_QUOTA),
                        ),
                    );
                }),
                http.get("/api/object_stores", ({ response }) => response(200).json(STORAGES)),
            );
            setupMockConfig({ enable_quotas: enableQuotas, quota_source_labels: Object.keys(usageBySource) });
            const pinia = createPinia();
            setActivePinia(pinia);
            useUserStore().currentUser = FAKE_USER;
            // The popover moves itself to the document body
            wrapper = mount(QuotaMeter as object, { global: withPlugins(localVue, pinia), attachTo: document.body });
            // As in the app, the usage per source arrives after the meter is shown
            await useQuotaUsageStore().loadQuotaUsages();
            await flushPromises();
        }

        it("names the sources whose quota the user exceeded", async () => {
            await mountWithSourceUsages({ secure: 1001, archive: 400 });

            expect(wrapper.find(OTHER_SOURCES_HINT).text()).toBe("Over quota on these storages: Secure Storage");
        });

        it("lists every source in a popover by its storages' names, marking those over quota", async () => {
            await mountWithSourceUsages({ scratch: 1001, archive: 400, secure: 1500 });

            const names = (selector: string) =>
                Array.from(
                    document.body.querySelectorAll(selector),
                    (row) => row.querySelector(SOURCE_NAME)?.textContent,
                );
            expect(names(SOURCE_USAGE)).toEqual(["Scratch Storage / Fast Scratch", "archive", "Secure Storage"]);
            expect(names(`${SOURCE_USAGE}.over-quota`)).toEqual(["Scratch Storage / Fast Scratch", "Secure Storage"]);
        });

        it("replaces the tooltip with the popover, which links to the storage dashboard", async () => {
            await mountWithSourceUsages({ scratch: 400, archive: 400 });

            expect(await hoverForTooltip(wrapper)).toBeNull();
            expect(document.body.querySelector(DASHBOARD_BUTTON)?.getAttribute("href")).toBe("/storage");
        });

        it("lists no sources when quotas are off, though other pages load their usage", async () => {
            await mountWithSourceUsages({ scratch: 400, archive: 400 }, { enableQuotas: false });

            expect(document.body.querySelector(SOURCE_USAGE)).toBeNull();
        });

        it("shows no hint while no source exceeds its quota", async () => {
            await mountWithSourceUsages({ scratch: SOURCE_QUOTA, archive: 400 });

            expect(wrapper.find(OTHER_SOURCES_HINT).exists()).toBe(false);
        });
    });
});
