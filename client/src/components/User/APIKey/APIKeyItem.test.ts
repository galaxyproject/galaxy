import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import APIKeyItem from "./APIKeyItem.vue";

vi.mock("@/app", () => ({
    getGalaxyInstance: () => ({ user: { id: "user-id" } }),
}));

vi.mock("./model/service", () => ({
    default: { deleteAPIKey: vi.fn() },
}));

const ITEM = { key: "abc123secret", create_time: "2026-11-01T10:00:00" };

function mountItem() {
    return mount(APIKeyItem as object, {
        props: { item: ITEM },
        global: getLocalVue(),
    });
}

describe("APIKeyItem.vue", () => {
    it("shows the key in a disabled password GFormInput", () => {
        const input = mountItem().get("[data-test-id='api-key-input']");
        expect(input.element.tagName).toBe("INPUT");
        expect(input.classes()).toContain("g-form-input");
        expect(input.attributes("type")).toBe("password");
        expect(input.attributes("disabled")).toBeDefined();
        expect((input.element as HTMLInputElement).value).toBe("abc123secret");
    });

    it("reveals and hides the key with the show/hide button", async () => {
        const wrapper = mountItem();
        const toggle = wrapper.get("[title='Show/hide key']");
        await toggle.trigger("click");
        expect(wrapper.get("[data-test-id='api-key-input']").attributes("type")).toBe("text");
        await toggle.trigger("click");
        expect(wrapper.get("[data-test-id='api-key-input']").attributes("type")).toBe("password");
    });
});
