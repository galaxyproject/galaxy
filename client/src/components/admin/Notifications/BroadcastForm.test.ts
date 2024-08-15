import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/jest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";

import { mockFetcher } from "@/api/schema/__mocks__";

import { generateNewBroadcast, generateRandomString } from "./test.utils";

import BroadcastForm from "./BroadcastForm.vue";

jest.mock("@/api/schema");

const SUBJECT_INPUT_SELECTOR = "#broadcast-subject";
const MESSAGE_INPUT_SELECTOR = "#broadcast-message";
const ACTION_LINK_SELECTOR = "#create-action-link";
const SUBMIT_BUTTON_SELECTOR = "#broadcast-submit";
const PUBLISHED_WARNING_SELECTOR = "#broadcast-published-warning";

const localVue = getLocalVue(true);

async function mountBroadcastForm(props?: object) {
    const pinia = createTestingPinia();
    setActivePinia(pinia);

    const mockRouter = {
        push: jest.fn(),
    };

    const wrapper = mount(BroadcastForm as object, {
        propsData: {
            ...props,
        },
        localVue,
        pinia,
        stubs: {
            FontAwesomeIcon: true,
        },
        mocks: {
            $router: mockRouter,
        },
    });

    await flushPromises();

    return { wrapper, mockRouter };
}

describe("BroadcastForm.vue", () => {
    function expectSubmitButton(wrapper: Wrapper<Vue>, enabled: boolean) {
        expect(wrapper.find(SUBMIT_BUTTON_SELECTOR).exists()).toBeTruthy();
        expect(wrapper.find(SUBMIT_BUTTON_SELECTOR).attributes("disabled")).toBe(enabled ? undefined : "disabled");
        expect(wrapper.find(SUBMIT_BUTTON_SELECTOR).attributes("title")).toBe(
            enabled ? "" : "Please fill all required fields"
        );
    }

    async function createBroadcast(wrapper: Wrapper<Vue>, mockRouter: { push: jest.Mock }, actionsLink = false) {
        mockFetcher.path("/api/notifications/broadcast").method("post").mock({ data: {} });

        expectSubmitButton(wrapper, false);

        await wrapper.find(SUBJECT_INPUT_SELECTOR).setValue("Test subject");
        await wrapper.find(MESSAGE_INPUT_SELECTOR).setValue("Test message");

        if (actionsLink) {
            await wrapper.find(ACTION_LINK_SELECTOR).trigger("click");

            await wrapper.vm.$nextTick();

            await wrapper.find("#broadcast-action-link-name-0").setValue("Test link name");
            await wrapper.find("#broadcast-action-link-link-0").setValue("https://test.link");
        }

        expectSubmitButton(wrapper, true);

        await wrapper.find(SUBMIT_BUTTON_SELECTOR).trigger("click");

        await wrapper.vm.$nextTick();

        expect(mockRouter.push).toHaveBeenCalledTimes(1);
        expect(mockRouter.push).toHaveBeenCalledWith("/admin/notifications");
    }

    it("should render form with empty fields and submit button disabled", async () => {
        const { wrapper } = await mountBroadcastForm();

        expectSubmitButton(wrapper, false);
    });

    it("should create broadcast when all inputs are defined", async () => {
        const { wrapper, mockRouter } = await mountBroadcastForm();

        await createBroadcast(wrapper, mockRouter);
    });

    it("should create broadcast with a link when all inputs are defined", async () => {
        const { wrapper, mockRouter } = await mountBroadcastForm();

        await createBroadcast(wrapper, mockRouter, true);
    });

    it("should get broadcast data when id is defined", async () => {
        const FAKE_BROADCAST = generateNewBroadcast({ actionLink: true });
        mockFetcher.path("/api/notifications/broadcast/{notification_id}").method("get").mock({ data: FAKE_BROADCAST });

        const { wrapper } = await mountBroadcastForm({ id: FAKE_BROADCAST.id });

        await wrapper.vm.$nextTick();

        expect((wrapper.find(SUBJECT_INPUT_SELECTOR).element as HTMLInputElement).value).toBe(
            FAKE_BROADCAST.content.subject
        );
        expect((wrapper.find(MESSAGE_INPUT_SELECTOR).element as HTMLInputElement).value).toBe(
            FAKE_BROADCAST.content.message
        );
        expect(wrapper.find("#broadcast-action-link-name-0").exists()).toBeTruthy();
        expect(wrapper.find("#broadcast-action-link-link-0").exists()).toBeTruthy();
    });

    it("should update broadcast when id is defined and all inputs are defined", async () => {
        const FAKE_BROADCAST = generateNewBroadcast({ actionLink: true });
        mockFetcher.path("/api/notifications/broadcast/{notification_id}").method("get").mock({ data: FAKE_BROADCAST });
        mockFetcher.path("/api/notifications/broadcast/{notification_id}").method("put").mock({ data: {} });

        const { wrapper, mockRouter } = await mountBroadcastForm({ id: FAKE_BROADCAST.id });

        const newSubject = generateRandomString();
        await wrapper.find(SUBJECT_INPUT_SELECTOR).setValue(newSubject);

        expectSubmitButton(wrapper, true);

        await wrapper.find(SUBMIT_BUTTON_SELECTOR).trigger("click");

        await wrapper.vm.$nextTick();

        expect(mockRouter.push).toHaveBeenCalledTimes(1);
        expect(mockRouter.push).toHaveBeenCalledWith("/admin/notifications");
    });

    it("should not show the published warning when editing a scheduled broadcast", async () => {
        const FAKE_BROADCAST = generateNewBroadcast({ published: false });
        mockFetcher.path("/api/notifications/broadcast/{notification_id}").method("get").mock({ data: FAKE_BROADCAST });

        const { wrapper } = await mountBroadcastForm({ id: FAKE_BROADCAST.id });

        expect(wrapper.find(PUBLISHED_WARNING_SELECTOR).exists()).toBeFalsy();
    });

    it("should show the published published when editing a published broadcast", async () => {
        const FAKE_BROADCAST = generateNewBroadcast({ published: true });
        mockFetcher.path("/api/notifications/broadcast/{notification_id}").method("get").mock({ data: FAKE_BROADCAST });

        const { wrapper } = await mountBroadcastForm({ id: FAKE_BROADCAST.id });

        expect(wrapper.find(PUBLISHED_WARNING_SELECTOR).exists()).toBeTruthy();
    });
});
