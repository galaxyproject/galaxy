import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/jest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { nextTick } from "vue";

import { generateMessageNotification, generateNewSharedItemNotification } from "@/components/Notifications/test-utils";
import { useNotificationsStore } from "@/stores/notificationsStore";

import NotificationCard from "@/components/Notifications/NotificationCard.vue";

const localVue = getLocalVue(true);

async function mountComponent(component: object, propsData: object = {}): Promise<Wrapper<Vue>> {
    const pinia = createTestingPinia();
    setActivePinia(pinia);

    const wrapper = mount(component, {
        localVue,
        propsData,
        pinia,
    });

    await flushPromises();
    return wrapper;
}

describe("Notifications categories", () => {
    it("render markdown in message notification", async () => {
        const notification = generateMessageNotification();
        notification.content.message = "This is a **markdown** message to test _rendering_";

        const wrapper = await mountComponent(NotificationCard, {
            notification,
        });

        expect(wrapper.find(`#g-card-description-${notification.id}`).html()).toContain(
            "This is a <strong>markdown</strong> message to test <em>rendering</em>"
        );
    });

    it("shared item notification show subject and message", async () => {
        const notification = generateNewSharedItemNotification();

        const wrapper = await mountComponent(NotificationCard, {
            notification,
        });

        expect(wrapper.text()).toContain(notification.content.item_type);
        expect(wrapper.text()).toContain(`The user ${notification.content.owner_name} shared`);

        expect(wrapper.find(`#g-card-description-${notification.id}`).text()).toContain(
            `The user ${notification.content.owner_name} shared`
        );
        expect(wrapper.find(`#g-card-description-${notification.id}`).text()).toContain(
            `${notification.content.item_type}  with you`
        );
    });

    it("mark as read", async () => {
        const notification = Math.random() > 0.5 ? generateMessageNotification() : generateNewSharedItemNotification();

        const wrapper = await mountComponent(NotificationCard, {
            notification: {
                ...notification,
                seen_time: null,
            },
        });

        const notificationsStore = useNotificationsStore();

        const spyOnUpdateNotification = jest.spyOn(notificationsStore, "updateNotification");
        spyOnUpdateNotification.mockImplementation(async (notification, changes) => {
            if (changes.deleted) {
                wrapper.setProps({
                    notification: null,
                });
            } else {
                wrapper.setProps({
                    notification: {
                        ...notification,
                        ...changes,
                    },
                });
            }
        });

        await flushPromises();

        spyOnUpdateNotification.mockImplementation(async (notification) => {
            wrapper.setProps({
                notification: {
                    ...notification,
                    seen_time: new Date().toISOString(),
                },
            });
        });

        const markAsReadButton = wrapper.find(`#g-card-action-mark-as-read-button-${notification.id}`);
        expect(markAsReadButton.exists()).toBe(true);
        await markAsReadButton.trigger("click");

        await nextTick();

        expect(spyOnUpdateNotification).toHaveBeenCalledTimes(1);

        expect(wrapper.find(`#g-card-action-expiration-time-button-${notification.id}`).exists()).toBe(true);
    });

    it("delete notification", async () => {
        const notification = Math.random() > 0.5 ? generateMessageNotification() : generateNewSharedItemNotification();

        const wrapper = await mountComponent(NotificationCard, {
            notification,
        });

        const notificationsStore = useNotificationsStore();

        const spyOnUpdateNotification = jest.spyOn(notificationsStore, "updateNotification");
        spyOnUpdateNotification.mockImplementation(async (_notification, changes) => {
            if (changes.deleted) {
                wrapper.setProps({
                    notification: null,
                });
            }
        });

        await flushPromises();

        const deleteButton = wrapper.find(`#g-card-action-delete-button-${notification.id}`);
        expect(deleteButton.exists()).toBe(true);
        await deleteButton.trigger("click");

        await nextTick();

        expect(spyOnUpdateNotification).toHaveBeenCalledTimes(1);
    });
});
