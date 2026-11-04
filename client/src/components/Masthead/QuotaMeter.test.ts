import { createTestingPinia } from "@pinia/testing";
import { getFakeQuotaUsageData, getFakeRegisteredUser } from "@tests/test-data";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { setupMockConfig } from "@tests/vitest/mockConfig";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { describe, expect, it, vi } from "vitest";

import type { RegisteredUser } from "@/api";
import { useServerMock } from "@/api/client/__mocks__";
import { useQuotaUsageStore } from "@/stores/quotaUsageStore";
import { useUserStore } from "@/stores/userStore";

import QuotaMeter from "./QuotaMeter.vue";

vi.mock("@/api/schema");

const localVue = getLocalVue();
const { server, http } = useServerMock();

const OTHER_SOURCES_HINT = "[data-description='other storage over quota']";

async function createQuotaMeterWrapper(config: any, user: RegisteredUser) {
    setupMockConfig(config);
    const pinia = createTestingPinia({ createSpy: vi.fn });
    const userStore = useUserStore();
    userStore.currentUser = user;
    const wrapper = mount(QuotaMeter as object, {
        global: localVue,
        pinia,
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

    it("displays tooltip", async () => {
        const config = { enable_quotas: true };
        const wrapper = await createQuotaMeterWrapper(config, FAKE_USER);
        expect(wrapper.attributes("title")).toContain("Storage");
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

        /** Mounts the meter with storage sources that each have a quota of ``SOURCE_QUOTA`` bytes. */
        async function mountWithSourceUsages(usageBySource: Record<string, number>) {
            server.use(
                http.get("/api/users/{user_id}/usage", ({ response }) => {
                    return response(200).json(
                        Object.entries(usageBySource).map(([label, usage]) =>
                            getFakeQuotaUsageData(label, usage, SOURCE_QUOTA),
                        ),
                    );
                }),
            );
            setupMockConfig({ enable_quotas: true, quota_source_labels: Object.keys(usageBySource) });
            const pinia = createPinia();
            setActivePinia(pinia);
            useUserStore().currentUser = FAKE_USER;
            await useQuotaUsageStore().loadQuotaUsages();
            const wrapper = mount(QuotaMeter as object, { global: withPlugins(localVue, pinia) });
            await flushPromises();
            return wrapper;
        }

        it("names the sources whose quota the user exceeded", async () => {
            const wrapper = await mountWithSourceUsages({ scratch: 1001, archive: 400 });

            expect(wrapper.find(OTHER_SOURCES_HINT).attributes("title")).toBe("Over quota on these storages: scratch");
        });

        it("shows no hint while no source exceeds its quota", async () => {
            const wrapper = await mountWithSourceUsages({ scratch: SOURCE_QUOTA, archive: 400 });

            expect(wrapper.find(OTHER_SOURCES_HINT).exists()).toBe(false);
        });
    });
});
