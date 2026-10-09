import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { UserNotification } from "@/api/notifications";
import { useNotificationsStore } from "@/stores/notificationsStore";

import { generateNotificationsList } from "./test-utils";

import NotificationsList from "./NotificationsList.vue";

const localVue = getLocalVue(true);

enableAutoUnmount(afterEach);

async function mountNotificationsList(notifications: UserNotification[]) {
    const pinia = createTestingPinia({ createSpy: vi.fn });
    setActivePinia(pinia);

    const notificationsStore = useNotificationsStore(pinia);
    notificationsStore.notifications = notifications;

    const wrapper = mount(NotificationsList, {
        global: {
            ...withPlugins(localVue, pinia),
            stubs: { ...localVue.stubs, FontAwesomeIcon: true },
        },
    });

    await flushPromises();
    return wrapper;
}

describe("NotificationsList", () => {
    it("render and count unread notifications", async () => {
        const { notifications, messageCount, sharedItemCount } = generateNotificationsList(10);
        const wrapper = await mountNotificationsList(notifications);

        expect(wrapper.findAll(".g-card")).toHaveLength(messageCount + sharedItemCount);

        const unreadNotification = wrapper.findAll(".unread-notification");
        expect(unreadNotification).toHaveLength(notifications.filter((notification) => !notification.seen_time).length);
        expect(unreadNotification).toHaveLength(6);
    });

    it("unread filter works", async () => {
        const { notifications } = generateNotificationsList(10);
        const wrapper = await mountNotificationsList(notifications);

        const unreadFilter = wrapper.find("#show-unread-filter");
        expect(unreadFilter.exists()).toBe(true);
        await unreadFilter.trigger("click");

        expect(wrapper.findAll(".g-card")).toHaveLength(
            notifications.filter((notification) => !notification.seen_time).length,
        );
        expect(wrapper.findAll(".g-card")).toHaveLength(6);
    });

    it("show no notifications message", async () => {
        const { notifications } = generateNotificationsList(10);
        const wrapper = await mountNotificationsList(notifications);
        expect(wrapper.find("#no-notifications").exists()).toBe(false);

        const notificationsStore = useNotificationsStore();
        notificationsStore.notifications = [];

        await wrapper.vm.$nextTick();

        expect(wrapper.find("#no-notifications").exists()).toBe(true);
    });
});
