import { getLocalVue, injectTestRouter } from "@tests/vitest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

import MountTarget from "./NewUserConfirmation.vue";

const localVue = getLocalVue(true);
const router = injectTestRouter(localVue);
const { server, http } = useServerMock();

interface PostRequest {
    url: string;
}

let postRequests: PostRequest[] = [];
let originalSearch: string;

describe("NewUserConfirmation", () => {
    let wrapper: Wrapper<Vue>;

    beforeEach(async () => {
        postRequests = [];

        // Navigate to a different route to avoid NavigationDuplicated error
        // when the component calls router.push("/") on successful submit
        await router.push("/new-user-confirmation").catch(() => {});

        // Mock window.location.search
        originalSearch = window.location.search;
        Object.defineProperty(window.location, "search", {
            configurable: true,
            writable: true,
            value: "?provider=test_provider&provider_token=sample_token",
        });

        server.use(
            http.untyped.post(/.*/, async ({ request }) => {
                postRequests.push({ url: request.url });
                return HttpResponse.json({});
            }),
        );

        wrapper = mount(MountTarget as object, {
            props: {},
            global: localVue,
        });
    });

    afterEach(() => {
        // Restore original search
        Object.defineProperty(window.location, "search", {
            configurable: true,
            writable: true,
            value: originalSearch,
        });
    });

    it("basics", async () => {
        const cardHeader = wrapper.find(".card-header");
        expect(cardHeader.text()).toBe("Confirm new account creation");

        const inputs = wrapper.findAll("input");
        expect(inputs.length).toBe(1);

        const checkField = inputs.at(0);
        expect(checkField.attributes("type")).toBe("checkbox");

        const submitButton = wrapper.find("button[name='confirm']");
        await submitButton.trigger("click");
        await flushPromises();

        expect(postRequests.length).toBe(0);

        await checkField.setChecked();

        await submitButton.trigger("click");
        await flushPromises();

        expect(postRequests.length).toBe(1);
        expect(postRequests[0]?.url).toContain("/authnz/test_provider/create_user");
        expect(postRequests[0]?.url).toContain("token=sample_token");

        await wrapper.setProps({ registrationWarningMessage: "registration warning message" });

        const alert = wrapper.find(".alert");
        expect(alert.text()).toBe("registration warning message");

        await wrapper.setProps({ termsUrl: "terms_url" });

        const termsFrame = wrapper.find("iframe");
        expect(termsFrame.attributes("src")).toBe("terms_url");

        const toggle = "a[id=login-toggle]";
        const loginToggle = wrapper.find(toggle);
        expect(loginToggle.text()).toBe("Log in here.");
    });
});
