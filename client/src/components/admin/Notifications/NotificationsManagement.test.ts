import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/jest/helpers";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";

import { mockFetcher } from "@/api/schema/__mocks__";

import NotificationsManagement from "./NotificationsManagement.vue";

jest.mock("@/api/schema");

const localVue = getLocalVue(true);

const selectors = {
    sendNotificationButton: "#send-notification-button",
    createBroadcastButton: "#create-broadcast-button",
} as const;

async function mountNotificationsManagement(config: any = {}) {
    const pinia = createTestingPinia();
    setActivePinia(pinia);

    mockFetcher.path("/api/configuration").method("get").mock({ data: config });

    const wrapper = shallowMount(NotificationsManagement as object, {
        localVue,
        pinia,
        stubs: {
            FontAwesomeIcon: true,
        },
    });

    await flushPromises();

    return wrapper;
}

describe("NotificationsManagement.vue", () => {
    it("should render the create notification buttons if the notification system is enabled", async () => {
        const config = { enable_notification_system: true };
        const wrapper = await mountNotificationsManagement(config);

        expect(wrapper.find(selectors.sendNotificationButton).exists()).toBe(true);
        expect(wrapper.find(selectors.createBroadcastButton).exists()).toBe(true);
    });

    it("should not render the create notification buttons if the notification system is disabled", async () => {
        const config = { enable_notification_system: false };
        const wrapper = await mountNotificationsManagement(config);

        expect(wrapper.find(selectors.sendNotificationButton).exists()).toBe(false);
        expect(wrapper.find(selectors.createBroadcastButton).exists()).toBe(false);
    });
});
