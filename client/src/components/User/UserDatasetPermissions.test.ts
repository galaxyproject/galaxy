import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import axios from "axios";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";

import UserDatasetPermissions from "./UserDatasetPermissions.vue";
import GAlert from "@/components/BaseComponents/GAlert.vue";
import DatasetPermissionsForm from "@/components/Dataset/DatasetPermissionsForm.vue";

vi.mock("axios", () => ({
    default: {
        get: vi.fn(),
        put: vi.fn(),
    },
}));

const localVue = getLocalVue();

describe("UserDatasetPermissions.vue", () => {
    it("replaces the loading form with an error when permissions cannot be loaded", async () => {
        vi.mocked(axios.get).mockRejectedValue(new Error("Request failed with status code 403"));

        const wrapper = shallowMount(UserDatasetPermissions as object, {
            localVue,
            propsData: { userId: "current" },
        });
        await flushPromises();

        expect(wrapper.findComponent(DatasetPermissionsForm).exists()).toBe(false);
        expect(wrapper.findComponent(GAlert).text()).toContain("Request failed with status code 403");
    });
});
