import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { afterEach, describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

import NotificationsManagement from "./NotificationsManagement.vue";

enableAutoUnmount(afterEach);

const selectors = {
    sendNotificationButton: "#send-notification-button",
    createBroadcastButton: "#create-broadcast-button",
} as const;

const { server, http } = useServerMock();

async function mountNotificationsManagement(enableNotificationSystem: boolean) {
    const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
    setActivePinia(pinia);

    server.use(
        http.get("/api/configuration", ({ response }) => {
            return response.untyped(HttpResponse.json({ enable_notification_system: enableNotificationSystem }));
        }),
    );

    const wrapper = shallowMount(NotificationsManagement, {
        global: getLocalVue(true),
        pinia,
        stubs: {
            FontAwesomeIcon: true,
        },
    });

    await flushPromises();

    return wrapper;
}

describe("NotificationsManagement.vue", () => {
    it.each([
        { state: "enabled", enabled: true },
        { state: "disabled", enabled: false },
    ])("shows creation buttons only when notifications are enabled: $state", async ({ enabled }) => {
        const wrapper = await mountNotificationsManagement(enabled);

        expect(wrapper.find(selectors.sendNotificationButton).exists()).toBe(enabled);
        expect(wrapper.find(selectors.createBroadcastButton).exists()).toBe(enabled);
    });
});
