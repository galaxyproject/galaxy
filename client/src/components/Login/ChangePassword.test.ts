import { getLocalVue, injectTestRouter } from "@tests/vitest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

import MountTarget from "./ChangePassword.vue";

const mockSafePath = vi.fn();
vi.mock("utils/redirect", () => ({
    withPrefix: mockSafePath,
}));

const localVue = getLocalVue(true);
const router = injectTestRouter(localVue);
const { server, http } = useServerMock();

interface PostRequest {
    url: string;
    data: Record<string, unknown>;
}

let postRequests: PostRequest[] = [];

describe("ChangePassword", () => {
    let wrapper: Wrapper<Vue>;

    beforeEach(() => {
        postRequests = [];
        server.use(
            http.untyped.post(/.*/, async ({ request }) => {
                const data = (await request.json()) as Record<string, unknown>;
                postRequests.push({ url: request.url, data });
                return HttpResponse.json({});
            }),
        );
        wrapper = mount(MountTarget as object, {
            propsData: {
                messageText: "message_text",
                messageVariant: "message_variant",
            },
            localVue,
            router,
        });
    });

    it("basics", async () => {
        const cardHeader = wrapper.find(".card-header");
        expect(cardHeader.text()).toBe("Change your password");

        const inputs = wrapper.findAll("input");
        expect(inputs.length).toBe(2);

        const firstPwdField = inputs.at(0);
        expect(firstPwdField.attributes("type")).toBe("password");

        await firstPwdField.setValue("test_first_pwd");

        const secondPwdField = inputs.at(1);
        expect(secondPwdField.attributes("type")).toBe("password");

        await secondPwdField.setValue("test_second_pwd");

        const submitButton = wrapper.find("button[type='submit']");

        await submitButton.trigger("submit");
        await flushPromises();

        expect(postRequests.length).toBe(1);
        expect(postRequests[0]?.data.password).toBe("test_first_pwd");
        expect(postRequests[0]?.data.confirm).toBe("test_second_pwd");
    });

    it("props", async () => {
        await wrapper.setProps({
            token: "test_token",
            expiredUser: "expired_user",
        });

        const input = wrapper.find("input");
        expect(input.attributes("type")).toBe("password");

        await input.setValue("current_password");

        const submitButton = wrapper.find("button[type='submit']");

        await submitButton.trigger("submit");
        await flushPromises();

        expect(postRequests.length).toBe(1);
        expect(postRequests[0]?.data.token).toBe("test_token");
        expect(postRequests[0]?.data.id).toBe("expired_user");
        expect(postRequests[0]?.data.current).toBe("current_password");

        const alert = wrapper.find(".alert");
        expect(alert.text()).toBe("message_text");
    });
});
