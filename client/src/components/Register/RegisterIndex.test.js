import { createTestingPinia } from "@pinia/testing";
import { mount } from "@vue/test-utils";
import { setActivePinia } from "pinia";
import { getLocalVue } from "tests/jest/helpers";

import MountTarget from "./RegisterIndex";

const mockPush = jest.fn();

jest.mock("vue-router/composables", () => ({
    useRoute: jest.fn(() => ({ name: "Home" })),
    useRouter: () => ({ push: mockPush }),
}));

const localVue = getLocalVue(true);

describe("RegisterIndex", () => {
    let wrapper;

    beforeEach(() => {
        const pinia = createTestingPinia();
        setActivePinia(pinia);

        wrapper = mount(MountTarget, {
            propsData: {
                allowUserCreation: false,
                sessionCsrfToken: "sessionCsrfToken",
            },
            localVue,
            pinia,
        });
    });

    it("switching from Register to Login", async () => {
        const cardHeader = wrapper.find(".card-header");
        expect(cardHeader.text()).toBeLocalizationOf("Create a Galaxy account");

        const loginToggle = wrapper.find("[id=login-toggle]");
        await loginToggle.trigger("click");

        expect(mockPush).toHaveBeenCalledWith("/login/start");
        expect(mockPush).toHaveBeenCalledTimes(1);
    });
});
