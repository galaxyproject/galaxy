import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { delay } from "msw";
import { createPinia, setActivePinia } from "pinia";
import { describe, expect, it } from "vitest";

import type { ConcreteObjectStoreModel } from "@/api";
import { useServerMock } from "@/api/client/__mocks__";
import { useQuotaUsageStore } from "@/stores/quotaUsageStore";

import ProvidedQuotaSourceUsageBar from "./ProvidedQuotaSourceUsageBar.vue";

const localVue = getLocalVue();
const { server, http } = useServerMock();

const USAGE = "[data-quota-usage]";

const OBJECT_STORE = {
    object_store_id: "default",
    private: false,
    badges: [],
    quota: { enabled: true, source: null },
} as unknown as ConcreteObjectStoreModel;

describe("ProvidedQuotaSourceUsageBar", () => {
    it("keeps showing the usage while it reloads", async () => {
        server.use(
            http.get("/api/users/{user_id}/usage", async ({ response }) => {
                await delay(20);
                return response(200).json([{ quota_source_label: null, total_disk_usage: 1024 }]);
            }),
        );
        const pinia = createPinia();
        setActivePinia(pinia);
        const wrapper = mount(ProvidedQuotaSourceUsageBar as object, {
            props: { objectStore: OBJECT_STORE },
            global: withPlugins(localVue, pinia),
        });
        await useQuotaUsageStore().loadQuotaUsages();
        await flushPromises();

        const reload = useQuotaUsageStore().loadQuotaUsages(true);
        await flushPromises();

        expect(wrapper.find(USAGE).exists()).toBe(true);
        await reload;
    });
});
