import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/jest/helpers";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";

import { useServerMock } from "@/api/client/__mocks__";
import { type BroadcastNotification } from "@/stores/broadcastsStore";

import { generateNewBroadcast } from "./test.utils";

import BroadcastsList from "./BroadcastsList.vue";

const localVue = getLocalVue(true);

const selectors = {
    emptyBroadcastsListAlert: "#empty-broadcast-list-alert",
    showActiveFilterButton: "#show-active-filter-button",
    showScheduledFilterButton: "#show-scheduled-filter-button",
    showExpiredFilterButton: "#show-expired-filter-button",
    broadcastItem: "[data-test-id='broadcast-item']",
} as const;

const { server, http } = useServerMock();

async function mountBroadcastsList(broadcasts?: BroadcastNotification[]) {
    const pinia = createTestingPinia();
    setActivePinia(pinia);

    server.use(
        http.get("/api/notifications/broadcast", ({ response }) => {
            return response(200).json(broadcasts ?? []);
        })
    );

    const wrapper = shallowMount(BroadcastsList as object, {
        localVue,
        pinia,
        stubs: {
            FontAwesomeIcon: true,
        },
    });

    await flushPromises();

    return wrapper;
}

describe("BroadcastsList.vue", () => {
    it("should render empty list message when there are no broadcasts", async () => {
        const wrapper = await mountBroadcastsList();

        expect(wrapper.findAll(selectors.broadcastItem).length).toBe(0);
        expect(wrapper.find(selectors.emptyBroadcastsListAlert).exists()).toBeTruthy();
    });

    it("should filter broadcasts by active, scheduled and expired", async () => {
        const now = Date.now();

        const activeBroadcast = {
            ...generateNewBroadcast({}),
            publication_time: new Date(now - 1000).toISOString(),
            expiration_time: new Date(now + 1000).toISOString(),
        };

        const scheduledBroadcast = {
            ...generateNewBroadcast({}),
            publication_time: new Date(now + 1000).toISOString(),
            expiration_time: new Date(now + 2000).toISOString(),
        };

        const expiredBroadcast = {
            ...generateNewBroadcast({}),
            publication_time: new Date(now - 2000).toISOString(),
            expiration_time: new Date(now - 1000).toISOString(),
        };

        const wrapper = await mountBroadcastsList([activeBroadcast, scheduledBroadcast, expiredBroadcast]);

        // All broadcasts are shown by default
        expect(wrapper.findAll(selectors.broadcastItem).length).toBe(3);

        // Disable all filters
        await wrapper.find(selectors.showActiveFilterButton).trigger("click");
        await wrapper.find(selectors.showScheduledFilterButton).trigger("click");
        await wrapper.find(selectors.showExpiredFilterButton).trigger("click");
        expect(wrapper.findAll(selectors.broadcastItem).length).toBe(0);
        expect(wrapper.find(selectors.emptyBroadcastsListAlert).exists()).toBeTruthy();

        // Enable active broadcasts filter
        await wrapper.find(selectors.showActiveFilterButton).trigger("click");
        expect(wrapper.findAll(selectors.broadcastItem).length).toBe(1);

        // Enable scheduled broadcasts filter
        await wrapper.find(selectors.showScheduledFilterButton).trigger("click");
        expect(wrapper.findAll(selectors.broadcastItem).length).toBe(2);

        // Enable expired broadcasts filter
        await wrapper.find(selectors.showExpiredFilterButton).trigger("click");
        expect(wrapper.findAll(selectors.broadcastItem).length).toBe(3);
    });
});
