import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/jest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import type Vue from "vue";

import { useServerMock } from "@/api/client/__mocks__";

import NotificationForm from "./NotificationForm.vue";

// Even though we don't use the API endpoints, this seems to prevent failure fetching
// openapi during jest testing.
useServerMock();

const SUBMIT_BUTTON_SELECTOR = "#notification-submit";

const localVue = getLocalVue(true);

async function mountNotificationForm(props?: object) {
    const pinia = createTestingPinia();
    setActivePinia(pinia);

    const wrapper = mount(NotificationForm as object, {
        propsData: {
            ...props,
        },
        localVue,
        pinia,
        stubs: {
            FontAwesomeIcon: true,
        },
    });

    await flushPromises();

    return { wrapper };
}

describe("NotificationForm.vue", () => {
    function expectSubmitButton(wrapper: Wrapper<Vue>, enabled: boolean) {
        expect(wrapper.find(SUBMIT_BUTTON_SELECTOR).exists()).toBeTruthy();
        expect(wrapper.find(SUBMIT_BUTTON_SELECTOR).attributes("disabled")).toBe(enabled ? undefined : "disabled");
        expect(wrapper.find(SUBMIT_BUTTON_SELECTOR).attributes("title")).toBe(
            enabled ? "" : "Please fill all required fields"
        );
    }

    it("should render form with empty fields and submit button disabled", async () => {
        const { wrapper } = await mountNotificationForm();

        expectSubmitButton(wrapper, false);

        await flushPromises();
    });
});
