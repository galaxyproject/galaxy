import { setActivePinia } from "pinia";
import flushPromises from "flush-promises";
import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "@tests/jest/helpers";
import { createTestingPinia } from "@pinia/testing";
import { mergeObjectListsById } from "@/utils/utils";
import NotificationsList from "./NotificationsList.vue";
import { generateNotificationsList } from "./test-utils";
import { useNotificationsStore } from "@/stores/notificationsStore";

const localVue = getLocalVue(true);

const { notifications: FAKE_NOTIFICATIONS, messageCount, sharedItemCount } = generateNotificationsList(10);

async function mountNotificationsList() {
    const pinia = createTestingPinia();
    setActivePinia(pinia);

    const notificationsStore = useNotificationsStore(pinia);
    notificationsStore.notifications = mergeObjectListsById(FAKE_NOTIFICATIONS, []);

    const wrapper = shallowMount(NotificationsList, {
        localVue,
        pinia,
    });

    await flushPromises();
    return wrapper;
}

describe("NotificationsList", () => {
    it("render and count unread notifications", async () => {
        const wrapper = await mountNotificationsList();
        expect(wrapper.findAll(".notification-card")).toHaveLength(messageCount + sharedItemCount);

        const unreadNotification = wrapper.findAll(".unread-status");
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
