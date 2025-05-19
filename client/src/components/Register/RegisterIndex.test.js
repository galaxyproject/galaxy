import { mount } from "@vue/test-utils";
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
        wrapper = mount(MountTarget, {
            propsData: {
                allowUserCreation: false,
                sessionCsrfToken: "sessionCsrfToken",
            },
            localVue,
        });
    });

    it("switching from Register to Login", async () => {
        const cardHeader = wrapper.find(".card-header");
        expect(cardHeader.text()).toBeLocalizationOf("Create a Galaxy account");
        const $loginToggle = "[id=login-toggle]";
        const loginToggle = wrapper.find($loginToggle);
        await loginToggle.trigger("click");
        expect(mockPush).toHaveBeenCalledWith("/login/start");
        expect(mockPush).toHaveBeenCalledTimes(1);
    });
});
