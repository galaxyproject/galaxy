import "@/composables/__mocks__/filter";

import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/jest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import type Vue from "vue";

import { useServerMock } from "@/api/client/__mocks__";

import NotificationForm from "./NotificationForm.vue";

// Calls roles, groups, and users APIs so we need to use a server mock
// to prevent attempts at making real API calls.
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
        expect(wrapper.find(SUBMIT_BUTTON_SELECTOR).attributes("aria-disabled")).toBe(enabled ? undefined : "true");
        expect(wrapper.find(SUBMIT_BUTTON_SELECTOR).attributes("data-title")).toBe(
            enabled ? "" : "Please fill all required fields",
        );
    }

    it("should render form with empty fields and submit button disabled", async () => {
        const { wrapper } = await mountNotificationForm();

        expectSubmitButton(wrapper, false);

        await flushPromises();
    });
});
