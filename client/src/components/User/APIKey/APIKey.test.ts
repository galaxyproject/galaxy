import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";

import svc from "./model/service";

import APIKey from "./APIKey.vue";

vi.mock("@/app", () => ({
    getGalaxyInstance: () => ({ user: { id: "user-id" } }),
}));

vi.mock("./model/service", () => ({
    default: {
        getAPIKey: vi.fn(),
        createNewAPIKey: vi.fn(),
        deleteAPIKey: vi.fn(),
    },
}));

const localVue = getLocalVue();

describe("APIKey.vue", () => {
    it("shows the error message when loading the key fails", async () => {
        vi.mocked(svc.getAPIKey).mockRejectedValue(new Error("Could not load the API key."));

        const wrapper = mount(APIKey as object, {
            global: { ...localVue, stubs: { ...localVue.stubs, BreadcrumbHeading: true } },
        });
        await flushPromises();

        const alert = wrapper.find(".alert-warning");
        expect(alert.exists()).toBe(true);
        expect(alert.text()).toContain("Could not load the API key.");
    });
});
