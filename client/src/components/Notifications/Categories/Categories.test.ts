import { setActivePinia } from "pinia";
import flushPromises from "flush-promises";
import { getLocalVue } from "@tests/jest/helpers";
import { createTestingPinia } from "@pinia/testing";
import { shallowMount, type Wrapper } from "@vue/test-utils";
import MessageNotification from "@/components/Notifications/Categories/MessageNotification.vue";
import SharedItemNotification from "@/components/Notifications/Categories/SharedItemNotification.vue";
import { generateMessageNotification, generateNewSharedItemNotification } from "@/components/Notifications/test-utils";

const localVue = getLocalVue(true);

async function mountComponent(
    component: typeof MessageNotification | typeof SharedItemNotification,
    propsData: object = {}
): Promise<Wrapper<Vue>> {
    const pinia = createTestingPinia();
    setActivePinia(pinia);

    const wrapper = shallowMount(component, {
        localVue,
        propsData,
        pinia,
    });

    await flushPromises();
    return wrapper;
}

function capitalizeFirstLetter(string: string) {
    return string.charAt(0).toUpperCase() + string.slice(1);
}

describe("Notifications categories", () => {
    it("render markdown in message notification", async () => {
        const notification = generateMessageNotification();
        notification.content.message = "This is a **markdown** message to test _rendering_";

        const wrapper = await mountComponent(MessageNotification, {
            notification,
        });

        expect(wrapper.find("#notification-message").html()).toContain(
            "This is a <strong>markdown</strong> message to test <em>rendering</em>"
        );
    });

    it("shared item notification show subject and message", async () => {
        const notification = generateNewSharedItemNotification();

        const wrapper = await mountComponent(SharedItemNotification, {
            notification,
        });

        expect(wrapper.text()).toContain(
            `${capitalizeFirstLetter(notification.content.item_type)} shared with you by ${
                notification.content.owner_name
            }`
        );

        expect(wrapper.find("#notification-message").text()).toContain(
            `The user ${notification.content.owner_name} shared`
        );
        expect(wrapper.find("#notification-message").text()).toContain(`${notification.content.item_type}  with you`);
    });
});
