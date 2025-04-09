import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/jest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";

import { type MessageNotification } from "@/api/notifications";
import { generateMessageNotification, generateNewSharedItemNotification } from "@/components/Notifications/test-utils";

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
        const notification: MessageNotification = generateMessageNotification();
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
});
