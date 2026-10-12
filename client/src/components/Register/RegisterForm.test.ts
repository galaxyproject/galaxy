import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, nth, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount, type VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { disposePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, onTestFinished, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import { sanitizeHtml } from "@/directives/sanitizeHtml";

import RegisterForm from "./RegisterForm.vue";

const localVue = getLocalVue(true);
const { server, http } = useServerMock();

// const SELECTORS = {
//     LOGIN_TOGGLE: "[id=login-toggle]",
// };

interface PostRequest {
    url: string;
    data: Record<string, unknown>;
}

let postRequests: PostRequest[] = [];

describe("RegisterForm", () => {
    let wrapper: VueWrapper<InstanceType<typeof RegisterForm>>;

    beforeEach(() => {
        postRequests = [];
        server.use(
            http.untyped.post(/.*/, async ({ request }) => {
                const data = (await request.json()) as Record<string, unknown>;
                postRequests.push({ url: request.url, data });
                return HttpResponse.json({});
            }),
        );

        const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
        onTestFinished(() => disposePinia(pinia));
        const router = createRouter({
            history: createMemoryHistory(),
            routes: [{ path: "/:pathMatch(.*)*", component: { template: "<div></div>" } }],
        });

        wrapper = mount(RegisterForm, {
            props: {
                sessionCsrfToken: "sessionCsrfToken",
            },
            global: withPlugins(localVue, pinia, router),
        });
    });

    afterEach(() => {
        vi.mocked(sanitizeHtml).mockClear();
    });
    enableAutoUnmount(afterEach);

    it("submits the entered email and password to create an account", async () => {
        const cardHeader = wrapper.get(".card-header");
        expect(cardHeader.text()).toBeLocalizationOf("Create a Galaxy account");

        const inputs = wrapper.findAll("input");
        expect(inputs.length).toBe(4);

        const emailField = nth(inputs, 0);
        expect(emailField.attributes("type")).toBe("text");
        await emailField.setValue("test_user");

        const pwdField = nth(inputs, 1);
        expect(pwdField.attributes("type")).toBe("password");
        await pwdField.setValue("test_pwd");

        const submitButton = wrapper.get("button[type='submit']");
        await submitButton.trigger("submit");
        await flushPromises();

        expect(postRequests.length).toBe(1);
        expect(postRequests[0]?.data.email).toBe("test_user");
        expect(postRequests[0]?.data.password).toBe("test_pwd");
    });

    it("sends the mailing list subscription when its checkbox is checked", async () => {
        await wrapper.setProps({ mailingJoinAddr: "announce@example.org", serverMailConfigured: true });

        await wrapper.get("input#register-form-subscribe").setValue(true);
        await wrapper.get("input#register-form-email").setValue("test_user");

        await wrapper.get("button[type='submit']").trigger("submit");
        await flushPromises();

        expect(postRequests.length).toBe(1);
        expect(postRequests[0]?.data.subscribe).toBe(true);
    });

    // TODO: Changing the original `<a>` to a `GLink` has made it so that the link never appears in the wrapper.
    // it("switching from Register to Login", async () => {
    //     const cardHeader = await wrapper.get(".card-header");
    //     expect(cardHeader.text()).toBeLocalizationOf("Create a Galaxy account");

    //     const loginToggle = wrapper.find(SELECTORS.LOGIN_TOGGLE); // TODO: Never appears because of the GLink change
    //     expect(loginToggle.exists()).toBeTruthy();

    //     await wrapper.setProps({ hideLoginLink: true });
    //     const missingToggle = wrapper.find(SELECTORS.LOGIN_TOGGLE);
    //     expect(missingToggle.exists()).toBeFalsy();
    // });

    it("renders the configured registration warning as written", async () => {
        vi.mocked(sanitizeHtml).mockClear();
        const message = 'Read the <a href="https://example.org/terms" target="_blank">terms</a>';
        await wrapper.setProps({ registrationWarningMessage: message });
        expect(sanitizeHtml).not.toHaveBeenCalledWith(message, expect.anything());
        expect(wrapper.get(".alert span").element.innerHTML).toBe(message);
    });
});
