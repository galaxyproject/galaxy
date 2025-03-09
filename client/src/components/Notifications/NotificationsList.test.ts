import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/jest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";

import { useNotificationsStore } from "@/stores/notificationsStore";
import { mergeObjectListsById } from "@/utils/utils";

import { generateNotificationsList } from "./test-utils";

import NotificationsList from "./NotificationsList.vue";

const localVue = getLocalVue(true);

const { notifications: FAKE_NOTIFICATIONS, messageCount, sharedItemCount } = generateNotificationsList(10);

async function mountNotificationsList() {
    const pinia = createTestingPinia();
    setActivePinia(pinia);

    const notificationsStore = useNotificationsStore(pinia);
    notificationsStore.notifications = mergeObjectListsById(FAKE_NOTIFICATIONS, []);

    const wrapper = mount(NotificationsList as object, {
        localVue,
        pinia,
        stubs: {
            FontAwesomeIcon: true,
        },
    });

    await flushPromises();
    return wrapper;
}

describe("NotificationsList", () => {
    it("render and count unread notifications", async () => {
        const wrapper = await mountNotificationsList();

        expect(wrapper.findAll(".notification-card")).toHaveLength(messageCount + sharedItemCount);

        const unreadNotification = wrapper.findAll(".unread-notification");
        expect(unreadNotification).toHaveLength(FAKE_NOTIFICATIONS.filter((n) => !n.seen_time).length);
    });

    it("unread filter works", async () => {
        const wrapper = await mountNotificationsList();

        const unreadFilter = wrapper.find("#show-unread-filter");
        expect(unreadFilter.exists()).toBe(true);
        unreadFilter.trigger("click");

        await wrapper.vm.$nextTick();

        expect(wrapper.findAll(".notification-card")).toHaveLength(
            FAKE_NOTIFICATIONS.filter((n) => !n.seen_time).length
        );
    });

    it("show no notifications message", async () => {
        const wrapper = await mountNotificationsList();
        expect(wrapper.find("#no-notifications").exists()).toBe(false);

        const notificationsStore = useNotificationsStore();
        notificationsStore.notifications = [];

        await wrapper.vm.$nextTick();

        expect(wrapper.find("#no-notifications").exists()).toBe(true);
    });
});
