import { getFakeRegisteredUser } from "@tests/test-data";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia, disposePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, onTestFinished, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import { useUserStore } from "@/stores/userStore";

import type { UserQuotaUsageData } from "./Quota/model/QuotaUsage";

import DiskUsageSummary from "./DiskUsageSummary.vue";

const localVue = getLocalVue();

const { server, http } = useServerMock();

const quotaUsageClassSelector = ".quota-usage";
const basicDiskUsageSummaryId = "#basic-disk-usage-summary";

const fakeUserWithQuota = getFakeRegisteredUser({
    total_disk_usage: 1000000,
    quota_bytes: 100000000,
    quota_percent: 1,
});

const fakeQuotaUsages: UserQuotaUsageData[] = [
    {
        quota_source_label: "Default",
        quota_bytes: 100000000,
        total_disk_usage: 1000000,
    },
];

const FAKE_TASK_ID = "fakeTaskId";

async function mountDiskUsageSummary(enableQuotas: boolean) {
    server.use(
        http.get("/api/configuration", ({ response }) => {
            return response.untyped(HttpResponse.json({ enable_quotas: enableQuotas }));
        }),
        http.get("/api/users/{user_id}", ({ response }) => {
            return response(200).json(fakeUserWithQuota);
        }),
        http.get("/api/users/{user_id}/usage", ({ response }) => {
            return response(200).json(fakeQuotaUsages);
        }),
    );

    const pinia = createPinia();
    onTestFinished(() => disposePinia(pinia));
    const wrapper = mount(DiskUsageSummary, {
        global: withPlugins(localVue, pinia),
    });
    const userStore = useUserStore(pinia);
    userStore.currentUser = fakeUserWithQuota;
    await flushPromises();
    return wrapper;
}

describe("DiskUsageSummary", () => {
    beforeEach(() => {
        vi.useFakeTimers();
    });
    afterEach(() => {
        vi.clearAllTimers();
        vi.useRealTimers();
    });
    enableAutoUnmount(afterEach);

    it("shows basic disk usage when quotas are disabled", async () => {
        const wrapper = await mountDiskUsageSummary(false);
        expect(wrapper.find(basicDiskUsageSummaryId).exists()).toBe(true);
        const quotaUsages = wrapper.findAll(quotaUsageClassSelector);
        expect(quotaUsages.length).toBe(0);
    });

    it("shows quota usage when quotas are enabled", async () => {
        const wrapper = await mountDiskUsageSummary(true);
        expect(wrapper.find(basicDiskUsageSummaryId).exists()).toBe(false);
        const quotaUsages = wrapper.findAll(quotaUsageClassSelector);
        expect(quotaUsages.length).toBe(1);
    });

    it("shows the quota usage in readable units", async () => {
        const wrapper = await mountDiskUsageSummary(true);
        const quotaUsage = wrapper.get(quotaUsageClassSelector);
        expect(quotaUsage.text()).toContain("1 MB");
    });

    it("refreshes quota usage after the pending recalculation task succeeds", async () => {
        const wrapper = await mountDiskUsageSummary(true);
        const quotaUsage = wrapper.get(quotaUsageClassSelector);
        expect(quotaUsage.text()).toContain("1 MB");
        const updatedFakeQuotaUsages: UserQuotaUsageData[] = [
            {
                quota_source_label: "Default",
                quota_bytes: 100000000,
                total_disk_usage: 2000000,
            },
        ];
        server.use(
            http.get("/api/users/{user_id}/usage", ({ response }) => {
                return response(200).json(updatedFakeQuotaUsages);
            }),
            http.put("/api/users/current/recalculate_disk_usage", ({ response }) => {
                return response(200).json({ id: FAKE_TASK_ID, ignored: false });
            }),
            http.get("/api/tasks/{task_id}/state", ({ response }) => {
                return response(200).json("PENDING");
            }),
        );
        const refreshButton = wrapper.get("#refresh-disk-usage");
        await refreshButton.trigger("click");
        await flushPromises();
        expect(wrapper.find(".refreshing-alert").exists()).toBe(true);

        server.use(
            http.get("/api/tasks/{task_id}/state", ({ response }) => {
                return response(200).json("SUCCESS");
            }),
        );
        vi.runAllTimers();
        await flushPromises();

        expect(wrapper.find(".refreshing-alert").exists()).toBe(false);
        expect(quotaUsage.text()).toContain("2 MB");
    });
});
