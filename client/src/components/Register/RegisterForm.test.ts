import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/jest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";

import MountTarget from "./RegisterForm.vue";

const localVue = getLocalVue(true);

describe("RegisterForm", () => {
    let wrapper: Wrapper<Vue>;
    let axiosMock: MockAdapter;

    beforeEach(() => {
        axiosMock = new MockAdapter(axios);

        const pinia = createTestingPinia();

        wrapper = mount(MountTarget as object, {
            propsData: {
                sessionCsrfToken: "sessionCsrfToken",
            },
            localVue,
            pinia,
        });
    });

    afterEach(() => {
        axiosMock.reset();
    });

    it("basics", async () => {
        const cardHeader = wrapper.find(".card-header");
        (expect(cardHeader.text()) as any).toBeLocalizationOf("Create a Galaxy account");

        const inputs = wrapper.findAll("input");
        expect(inputs.length).toBe(4);

        const usernameField = inputs.at(0);
        expect(usernameField.attributes("type")).toBe("text");
        await usernameField.setValue("test_user");

        const pwdField = inputs.at(1);
        expect(pwdField.attributes("type")).toBe("password");
        await pwdField.setValue("test_pwd");

        const submitButton = wrapper.find("button[type='submit']");
        await submitButton.trigger("submit");

        const postedData = JSON.parse(axiosMock.history.post?.[0]?.data);
        expect(postedData.email).toBe("test_user");
        expect(postedData.password).toBe("test_pwd");
    });
});

// ------- The test for the removed `RegisterIndex` component -------
// TODO: Merge/Add this test here in `RegisterForm.test.ts`

// const mockPush = jest.fn();

// jest.mock("vue-router/composables", () => ({
//     useRoute: jest.fn(() => ({ name: "Home" })),
//     useRouter: () => ({ push: mockPush }),
// }));

// describe("RegisterIndex", () => {
//     let wrapper;

//     beforeEach(() => {
//         const pinia = createTestingPinia();

//         wrapper = mount(RegisterIndex, {
//             propsData: {
//                 allowUserCreation: false,
//                 sessionCsrfToken: "sessionCsrfToken",
//             },
//             localVue,
//             pinia,
//         });
//     });

//     it("switching from Register to Login", async () => {
//         const cardHeader = wrapper.find(".card-header");
//         expect(cardHeader.text()).toBeLocalizationOf("Create a Galaxy account");

//         const loginToggle = wrapper.find("[id=login-toggle]");
//         await loginToggle.trigger("click");

//         expect(mockPush).toHaveBeenCalledWith("/login/start");
//         expect(mockPush).toHaveBeenCalledTimes(1);
//     });
// });
