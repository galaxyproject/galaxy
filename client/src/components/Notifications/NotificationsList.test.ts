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

async function mountNotificationsList(notifications: UserNotification[], attachTo?: HTMLElement) {
    const pinia = createTestingPinia({ createSpy: vi.fn });
    setActivePinia(pinia);

    const notificationsStore = useNotificationsStore(pinia);
    notificationsStore.notifications = notifications;

    const wrapper = mount(NotificationsList, {
        global: {
            ...withPlugins(localVue, pinia),
            stubs: { ...localVue.stubs, FontAwesomeIcon: true },
        },
        attachTo,
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

    it("selects all from a partial selection, then none, keeping the header box in sync", async () => {
        // Attached, so a native click on the box dispatches change
        const { notifications } = generateNotificationsList(10);
        const wrapper = await mountNotificationsList(notifications, document.body);
        const header = wrapper.get(".notifications-list-filter-selection");
        const headerBox = header.get<HTMLInputElement>("input[type='checkbox']");
        const total = notifications.length;

        await wrapper.get(".g-card-select-checkbox input").setValue(true);
        expect(wrapper.findAll(".g-card-select-checkbox input:checked")).toHaveLength(1);

        headerBox.element.click();
        await flushPromises();
        expect(wrapper.findAll(".g-card-select-checkbox input:checked")).toHaveLength(total);
        expect(headerBox.element.checked).toBe(true);
        expect(header.text()).toContain(`${total} selected`);

        headerBox.element.click();
        await flushPromises();
        expect(wrapper.findAll(".g-card-select-checkbox input:checked")).toHaveLength(0);
        expect(headerBox.element.checked).toBe(false);
        expect(header.text()).toContain("Select all");

        wrapper.unmount();
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
