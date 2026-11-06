import { getFakeRegisteredUser } from "@tests/test-data";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
import { defineComponent } from "vue";

import type { AnonymousUser, AnyUser } from "@/api";
import { useServerMock } from "@/api/client/__mocks__";
import { useUserStore } from "@/stores/userStore";

import { useOtherQuotaSourcesUsage } from "./otherQuotaSources";

const { server, http } = useServerMock();

describe("useOtherQuotaSourcesUsage", () => {
    let usageRequests: number;

    beforeEach(() => {
        setActivePinia(createPinia());
        usageRequests = 0;
        server.use(
            http.get("/api/users/{user_id}/usage", ({ response }) => {
                usageRequests++;
                return response(200).json([]);
            }),
        );
    });

    async function startLoading(user: AnyUser, quotaSourceLabels: string[], { enableQuotas = true } = {}) {
        useUserStore().currentUser = user;
        server.use(
            http.get("/api/configuration", ({ response }) =>
                response(200).json({
                    enable_quotas: enableQuotas,
                    quota_source_labels: quotaSourceLabels,
                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                } as any),
            ),
        );
        mount(defineComponent({ setup: () => useOtherQuotaSourcesUsage(), render: () => null }));
        await flushPromises();
    }

    it("loads for a registered user on a server with other sources", async () => {
        await startLoading(getFakeRegisteredUser(), ["scratch"]);

        expect(usageRequests).toBe(1);
    });

    it("doesn't load on a server without other sources", async () => {
        await startLoading(getFakeRegisteredUser(), []);

        expect(usageRequests).toBe(0);
    });

    it("doesn't load with quotas off", async () => {
        await startLoading(getFakeRegisteredUser(), ["scratch"], { enableQuotas: false });

        expect(usageRequests).toBe(0);
    });

    it("doesn't load for an anonymous user", async () => {
        const anonymous: AnonymousUser = {
            isAnonymous: true,
            total_disk_usage: 0,
            nice_total_disk_usage: "0 bytes",
            quota_percent: 0,
        };
        await startLoading(anonymous, ["scratch"]);

        expect(usageRequests).toBe(0);
    });

    it("loads once a user arrives after the page started", async () => {
        await startLoading(null, ["scratch"]);
        expect(usageRequests).toBe(0);

        useUserStore().currentUser = getFakeRegisteredUser();
        await flushPromises();

        expect(usageRequests).toBe(1);
    });
});
