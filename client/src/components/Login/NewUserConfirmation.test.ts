import { getLocalVue, injectTestRouter } from "@tests/vitest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

import MountTarget from "./NewUserConfirmation.vue";

const localVue = getLocalVue(true);
const router = injectTestRouter(localVue);
const { server, http } = useServerMock();

interface PostRequest {
    url: string;
    body: URLSearchParams;
}

let postRequests: PostRequest[] = [];
let originalSearch: string;

describe("NewUserConfirmation", () => {
    let wrapper: Wrapper<Vue>;

    beforeEach(async () => {
        postRequests = [];
        vi.spyOn(window.location, "assign").mockImplementation(() => {});

        await router.push("/new-user-confirmation").catch(() => {});

        // Mock window.location.search
        originalSearch = window.location.search;
        Object.defineProperty(window.location, "search", {
            configurable: true,
            writable: true,
            value: "?provider=test_provider&confirmation_id=sample_confirmation",
        });

        server.use(
            http.untyped.post(/.*/, async ({ request }) => {
                postRequests.push({ url: request.url, body: new URLSearchParams(await request.text()) });
                return HttpResponse.json({});
            }),
        );

        wrapper = mount(MountTarget as object, {
            propsData: { sessionCsrfToken: "session-csrf-token" },
            localVue,
            router,
        });
    });

    afterEach(() => {
        wrapper.destroy();
        vi.restoreAllMocks();
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
        expect(new URL(postRequests[0]!.url).search).toBe("");
        expect(postRequests[0]?.body.get("confirmation_id")).toBe("sample_confirmation");
        expect(postRequests[0]?.body.get("session_csrf_token")).toBe("session-csrf-token");
        expect(postRequests[0]?.body.has("token")).toBe(false);

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

    it("rejects form submission until terms are accepted", async () => {
        await wrapper.find("form").trigger("submit");
        await flushPromises();
        expect(postRequests).toHaveLength(0);
    });

    it.each([
        { root: "/", redirectUri: "/user/external_ids", expected: "/user/external_ids" },
        { root: "/galaxy", redirectUri: "/galaxy/user/external_ids", expected: "/galaxy/user/external_ids" },
        { root: "/galaxy", redirectUri: undefined, expected: "/galaxy/" },
    ])("reloads the session at $expected after confirmation", async ({ root, redirectUri, expected }) => {
        const indexLink = document.createElement("link");
        indexLink.rel = "index";
        indexLink.href = root;
        document.head.prepend(indexLink);
        try {
            server.use(http.untyped.post(/.*create_user$/, () => HttpResponse.json({ redirect_uri: redirectUri })));
            await wrapper.find("input[type='checkbox']").setChecked();
            await wrapper.find("button[name='confirm']").trigger("click");
            await flushPromises();
            expect(window.location.assign).toHaveBeenCalledExactlyOnceWith(expected);
            expect(router.currentRoute.path).toBe("/new-user-confirmation");
        } finally {
            indexLink.remove();
        }
    });

    it("cancels the server confirmation before returning to login", async () => {
        await wrapper.find("button[name='cancel']").trigger("click");
        await flushPromises();
        expect(postRequests).toHaveLength(1);
        expect(postRequests[0]?.url).toContain("/cancel_user_creation");
        expect(postRequests[0]?.body.get("confirmation_id")).toBe("sample_confirmation");
        expect(postRequests[0]?.body.get("session_csrf_token")).toBe("session-csrf-token");
        expect(router.currentRoute.path).toBe("/login");
    });

    it("shows expiry errors without redirecting", async () => {
        server.use(
            http.untyped.post(/.*create_user$/, () =>
                HttpResponse.json(
                    { err_msg: "Authentication expired. Please start logging in again." },
                    { status: 400 },
                ),
            ),
        );
        await wrapper.find("input[type='checkbox']").setChecked();
        await wrapper.find("button[name='confirm']").trigger("click");
        await flushPromises();
        expect(wrapper.find(".alert-danger").text()).toContain("Authentication expired");
        expect(router.currentRoute.path).toBe("/new-user-confirmation");
        expect(window.location.assign).not.toHaveBeenCalled();
    });

    it("prevents duplicate submissions while a request is pending", async () => {
        let finish: (() => void) | undefined;
        server.use(
            http.untyped.post(/.*create_user$/, async ({ request }) => {
                postRequests.push({ url: request.url, body: new URLSearchParams(await request.text()) });
                await new Promise<void>((resolve) => {
                    finish = resolve;
                });
                return HttpResponse.json({ redirect_uri: "/" });
            }),
        );
        await wrapper.find("input[type='checkbox']").setChecked();
        await wrapper.find("form").trigger("submit");
        await flushPromises();
        expect(wrapper.find("button[name='confirm']").attributes("disabled")).toBeDefined();
        await wrapper.find("form").trigger("submit");
        await flushPromises();
        expect(postRequests).toHaveLength(1);
        finish!();
        await flushPromises();
    });

    it("never resubmits credentials from a legacy link", async () => {
        wrapper.destroy();
        Object.defineProperty(window.location, "search", {
            configurable: true,
            writable: true,
            value: "?provider=test_provider&provider_token=secret-provider-response",
        });
        wrapper = mount(MountTarget as object, {
            propsData: { sessionCsrfToken: "session-csrf-token" },
            localVue,
            router,
        });
        await wrapper.find("input[type='checkbox']").setChecked();
        await wrapper.find("form").trigger("submit");
        await flushPromises();
        expect(postRequests).toHaveLength(0);
        expect(wrapper.find(".alert-danger").text()).toContain("Please start logging in again");
        expect(wrapper.text()).not.toContain("secret-provider-response");
    });
});
