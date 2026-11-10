import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

import DeviceVerification from "./DeviceVerification.vue";

const globalConfig = getLocalVue();
const { server, http } = useServerMock();

const DEVICE_AUTHORIZATION_URL = /\/api\/oauth\/device_authorization\/.+/;

const DETAILS = {
    user_code: "WDJB-MJHT",
    client_id: "galaxy-cli",
    app_name: "Galaxy CLI",
    scopes: ["histories:read", "tools:run"],
    requesting_ip: "203.0.113.7",
    create_time: "2026-11-10T21:51:54",
    expires_at: "2026-11-10T22:06:54",
};

function errorResponse(status: number, errMsg: string, reason?: string) {
    return HttpResponse.json({ err_msg: errMsg, err_code: status * 1000 + 1, ...(reason && { reason }) }, { status });
}

function mockLookUpSucceeds() {
    server.use(http.get("/api/oauth/device_authorization/{user_code}", ({ response }) => response(200).json(DETAILS)));
}

async function mountAndEnterCode(code = "wdjb-mjht") {
    const wrapper = mount(DeviceVerification as object, { global: globalConfig });
    await wrapper.find("#device-user-code").setValue(code);
    await wrapper.find("#device-code-form").trigger("submit");
    await flushPromises();
    return wrapper;
}

describe("DeviceVerification", () => {
    it.each([
        [true, "Login approved"],
        [false, "Login denied"],
    ])("shows the requesting app and records approve=%s", async (approve, heading) => {
        mockLookUpSucceeds();
        let sentBody: unknown;
        server.use(
            http.put("/api/oauth/device_authorization/{user_code}", async ({ request, response }) => {
                sentBody = await request.json();
                return response(204).empty();
            }),
        );
        const wrapper = await mountAndEnterCode();

        expect(wrapper.text()).toContain("Galaxy CLI");
        expect(wrapper.text()).toContain("histories:read");
        expect(wrapper.text()).toContain("203.0.113.7");

        await wrapper.find(approve ? "#device-approve" : "#device-deny").trigger("click");
        await flushPromises();

        expect(sentBody).toEqual({ approve });
        expect(wrapper.text()).toContain(heading);
    });

    it("shows a dead code under the field and keeps Continue off until the code changes", async () => {
        server.use(
            http.untyped.get(DEVICE_AUTHORIZATION_URL, () => errorResponse(404, "No login request found.", "unknown")),
        );
        const wrapper = await mountAndEnterCode("BBBB-BBBB");
        const continueButton = () => wrapper.find("#device-code-form button[type='submit']");

        expect(wrapper.find("#device-user-code-feedback").text()).toContain("No login request found.");
        expect(wrapper.find("#device-user-code").attributes("aria-invalid")).toBe("true");
        expect(continueButton().attributes("aria-disabled")).toBe("true");

        await wrapper.find("#device-user-code").setValue("BBBB-BBBC");

        expect(wrapper.find("#device-user-code-feedback").exists()).toBe(false);
        expect(continueButton().attributes("aria-disabled")).toBeUndefined();
    });

    it("keeps Continue on when the lookup fails for another reason", async () => {
        server.use(http.untyped.get(DEVICE_AUTHORIZATION_URL, () => errorResponse(500, "Internal server error.")));
        const wrapper = await mountAndEnterCode();

        expect(wrapper.find("#device-user-code-feedback").text()).toContain("Internal server error.");
        expect(wrapper.find("#device-code-form button[type='submit']").attributes("aria-disabled")).toBeUndefined();
    });

    it("offers a different code when the code expired before approving", async () => {
        mockLookUpSucceeds();
        server.use(
            http.untyped.put(DEVICE_AUTHORIZATION_URL, () => errorResponse(409, "This code has expired.", "expired")),
        );
        const wrapper = await mountAndEnterCode();

        await wrapper.find("#device-approve").trigger("click");
        await flushPromises();

        expect(wrapper.text()).toContain("This code has expired.");
        expect(wrapper.find("#device-approve").exists()).toBe(false);

        await wrapper.find("#device-start-over").trigger("click");

        expect(wrapper.find("#device-user-code").exists()).toBe(true);
    });

    it("keeps Approve and Deny when approving fails for another reason", async () => {
        mockLookUpSucceeds();
        server.use(http.untyped.put(DEVICE_AUTHORIZATION_URL, () => errorResponse(500, "Internal server error.")));
        const wrapper = await mountAndEnterCode();

        await wrapper.find("#device-approve").trigger("click");
        await flushPromises();

        expect(wrapper.text()).toContain("Internal server error.");
        expect(wrapper.find("#device-approve").exists()).toBe(true);
        expect(wrapper.find("#device-start-over").exists()).toBe(false);
    });
});
