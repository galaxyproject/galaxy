import { getFakeRegisteredUser } from "@tests/test-data";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia } from "pinia";
import { getLocalVue } from "tests/jest/helpers";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import { useUserStore } from "@/stores/userStore";

import { type UserQuotaUsageData } from "./Quota/model/QuotaUsage";

import DiskUsageSummary from "./DiskUsageSummary.vue";

const localVue = getLocalVue();

const { server, http } = useServerMock();

const quotaUsageClassSelector = ".quota-usage";
const basicDiskUsageSummaryId = "#basic-disk-usage-summary";

const fakeUserWithQuota = getFakeRegisteredUser({
    total_disk_usage: 1048576,
    quota_bytes: 104857600,
    quota_percent: 1,
});

const fakeQuotaUsages: UserQuotaUsageData[] = [
    {
        quota_source_label: "Default",
        quota_bytes: 104857600,
        total_disk_usage: 1048576,
    },
];

const FAKE_TASK_ID = "fakeTaskId";

async function mountDiskUsageSummaryWrapper(enableQuotas: boolean) {
    server.use(
        http.get("/api/configuration", ({ response }) => {
            return response.untyped(HttpResponse.json({ enable_quotas: enableQuotas }));
        }),
        http.get("/api/users/{user_id}", ({ response }) => {
            return response(200).json(fakeUserWithQuota);
        }),
        http.get("/api/users/{user_id}/usage", ({ response }) => {
            return response(200).json(fakeQuotaUsages);
        })
    );

    const pinia = createPinia();
    const wrapper = mount(DiskUsageSummary, {
        localVue,
        pinia,
    });
    const userStore = useUserStore();
    userStore.currentUser = fakeUserWithQuota;
    await flushPromises();
    return wrapper;
}

describe("DiskUsageSummary.vue", () => {
    jest.useFakeTimers();
    it("should display basic disk usage summary if quotas are NOT enabled", async () => {
        const enableQuotasInConfig = false;
        const wrapper = await mountDiskUsageSummaryWrapper(enableQuotasInConfig);
        expect(wrapper.find(basicDiskUsageSummaryId).exists()).toBe(true);
        const quotaUsages = wrapper.findAll(quotaUsageClassSelector);
        expect(quotaUsages.length).toBe(0);
    });

    it("should display quota usage summary if quotas are enabled", async () => {
        const enableQuotasInConfig = true;
        const wrapper = await mountDiskUsageSummaryWrapper(enableQuotasInConfig);
        expect(wrapper.find(basicDiskUsageSummaryId).exists()).toBe(false);
        const quotaUsages = wrapper.findAll(quotaUsageClassSelector);
        expect(quotaUsages.length).toBe(1);
    });

    it("should display the correct quota usage", async () => {
        const enableQuotasInConfig = true;
        const wrapper = await mountDiskUsageSummaryWrapper(enableQuotasInConfig);
        const quotaUsage = wrapper.find(quotaUsageClassSelector);
        expect(quotaUsage.text()).toContain("1 MB");
    });

    it("should refresh the quota usage when the user clicks the refresh button", async () => {
        const enableQuotasInConfig = true;
        const wrapper = await mountDiskUsageSummaryWrapper(enableQuotasInConfig);
        const quotaUsage = wrapper.find(quotaUsageClassSelector);
        expect(quotaUsage.text()).toContain("1 MB");
        const updatedFakeQuotaUsages: UserQuotaUsageData[] = [
            {
                quota_source_label: "Default",
                quota_bytes: 104857600,
                total_disk_usage: 2097152,
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
            })
        );
        const refreshButton = wrapper.find("#refresh-disk-usage");
        await refreshButton.trigger("click");
        await flushPromises();
        expect(wrapper.find(".refreshing-alert").exists()).toBe(true);

        // Make sure the refresh has finished before checking the quota usage
        server.use(
            http.get("/api/tasks/{task_id}/state", ({ response }) => {
                return response(200).json("SUCCESS");
            })
        );
        jest.runAllTimers();
        await flushPromises();

        // The refreshing alert should disappear and the quota usage should be updated
        expect(wrapper.find(".refreshing-alert").exists()).toBe(false);
        expect(quotaUsage.text()).toContain("2 MB");
    });
});
