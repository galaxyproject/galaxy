import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount, shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";

import { type QuotaUsage, toQuotaUsage } from "./model";

import QuotaUsageSummary from "./QuotaUsageSummary.vue";

const localVue = getLocalVue(true);
const { server, http } = useServerMock();

const QUOTA_1_BYTES = 654846535;
const QUOTA_2_BYTES = 68468436;

const DEFAULT_SOURCE_USAGE = toQuotaUsage({
    quota_source_label: null,
    quota_bytes: QUOTA_1_BYTES,
    total_disk_usage: 0,
});

const FAKE_QUOTA_USAGES_LIST: QuotaUsage[] = [
    toQuotaUsage({
        quota_source_label: "source 1",
        quota_bytes: QUOTA_1_BYTES,
        total_disk_usage: QUOTA_1_BYTES,
    }),
    toQuotaUsage({
        quota_source_label: "source 2",
        quota_bytes: QUOTA_2_BYTES,
        total_disk_usage: QUOTA_2_BYTES,
    }),
    toQuotaUsage({
        quota_source_label: "Unlimited source",
        quota_bytes: undefined,
        total_disk_usage: 0,
    }),
];

function mountQuotaUsageSummaryWith(quotaUsages: QuotaUsage[]) {
    const wrapper = shallowMount(QuotaUsageSummary as object, { props: { quotaUsages }, localVue });
    return wrapper;
}

describe("QuotaUsageSummary.vue", () => {
    it("should calculate the total amount of quotas without the unlimited", () => {
        const wrapper = mountQuotaUsageSummaryWith(FAKE_QUOTA_USAGES_LIST);
        const expectedTotalBytes = QUOTA_1_BYTES + QUOTA_2_BYTES;
        // TODO: explicit any because the type of the vm is not correctly inferred, remove when fixed
        expect((wrapper.vm as any).totalQuotaInBytes).toBe(expectedTotalBytes);
    });

    it("should display a quota bar for each quota", () => {
        const wrapper = mountQuotaUsageSummaryWith(FAKE_QUOTA_USAGES_LIST);
        const expectedNumberOfBars = FAKE_QUOTA_USAGES_LIST.length;

        expect(wrapper.findAll(".quota-usage-bar").length).toBe(expectedNumberOfBars);
    });

    it("should display `unlimited` quota when all sources are unlimited", async () => {
        const FAKE_UNLIMITED_QUOTA_USAGES: QuotaUsage[] = [
            toQuotaUsage({
                quota_source_label: "Unlimited source 1",
                quota_bytes: undefined,
                total_disk_usage: QUOTA_1_BYTES,
            }),
            toQuotaUsage({
                quota_source_label: "Unlimited source 2",
                quota_bytes: undefined,
                total_disk_usage: QUOTA_2_BYTES,
            }),
        ];
        const wrapper = mountQuotaUsageSummaryWith(FAKE_UNLIMITED_QUOTA_USAGES);
        const summaryText = wrapper.find("h2").text();
        expect(summaryText).toContain("unlimited");
    });

    describe("source names", () => {
        async function sourceNamesShownFor(quotaUsages: QuotaUsage[]) {
            server.use(http.get("/api/object_stores", ({ response }) => response(200).json([])));
            const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
            const wrapper = mount(QuotaUsageSummary as object, {
                props: { quotaUsages },
                global: { plugins: [pinia] },
            });
            await flushPromises();
            return wrapper.findAll(".storage-source-label").map((label) => label.text());
        }

        it("names the default source when other sources are shown", async () => {
            const names = await sourceNamesShownFor([DEFAULT_SOURCE_USAGE, ...FAKE_QUOTA_USAGES_LIST]);
            expect(names).toEqual(["Default storage", "source 1", "source 2", "Unlimited source"]);
        });

        it("leaves the default source unnamed when it is the only one", async () => {
            expect(await sourceNamesShownFor([DEFAULT_SOURCE_USAGE])).toEqual([]);
        });
    });
});
