import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import { computed } from "vue";
import VueRouter from "vue-router";

import { hasSingleOidcProfile } from "@/components/User/ExternalIdentities/ExternalIDHelper";
import { useConfig } from "@/composables/config";

import UserPreferences from "./UserPreferences.vue";

vi.mock("@/composables/config", () => ({
    useConfig: vi.fn(),
}));

vi.mock("@/components/User/ExternalIdentities/ExternalIDHelper", () => ({
    hasSingleOidcProfile: vi.fn(),
}));

vi.mock("@/app", () => ({
    getGalaxyInstance: () => ({
        session_csrf_token: "mock-token",
    }),
}));

vi.mock("@/components/User/UserPreferencesModel", () => ({
    getUserPreferencesModel: () => ({}),
}));

vi.mock("@/composables/confirmDialog", () => ({
    useConfirmDialog: () => ({
        confirm: vi.fn(),
    }),
}));

const localVue = getLocalVue();
localVue.use(VueRouter);

describe("UserPreferences.vue", () => {
    it("shows oidc-profile element when OIDC is enabled and configured correctly", async () => {
        vi.mocked(useConfig).mockReturnValue({
            config: computed(() => ({
                enable_oidc: true,
                disable_local_accounts: true,
                oidc: {},
                themes: [],
            })),
            isConfigLoaded: computed(() => true),
        });

        vi.mocked(hasSingleOidcProfile).mockReturnValue(true);

        const wrapper = shallowMount(UserPreferences, {
            localVue,
            router: new VueRouter(),
            pinia: createTestingPinia({ createSpy: vi.fn }),
            stubs: {
                BreadcrumbHeading: true,
                UserDetailsElement: true,
                UserPreferencesElement: true,
                Heading: true,
                BAlert: true,
                BModal: true,
                UserPickTheme: true,
                UserBeaconSettings: true,
                UserPreferredObjectStore: true,
                UserDeletion: true,
            },
        });

        expect(wrapper.find("#oidc-profile").exists()).toBe(true);
    });

    it("does not show oidc-profile element when profile_url is not set", async () => {
        vi.mocked(useConfig).mockReturnValue({
            config: computed(() => ({
                enable_oidc: true,
                disable_local_accounts: true,
                oidc: {},
                themes: [],
            })),
            isConfigLoaded: computed(() => true),
        });

        vi.mocked(hasSingleOidcProfile).mockReturnValue(false);

        const wrapper = shallowMount(UserPreferences, {
            localVue,
            router: new VueRouter(),
            pinia: createTestingPinia({ createSpy: vi.fn }),
            stubs: {
                BreadcrumbHeading: true,
                UserDetailsElement: true,
                UserPreferencesElement: true,
                Heading: true,
                BAlert: true,
                BModal: true,
                UserPickTheme: true,
                UserBeaconSettings: true,
                UserPreferredObjectStore: true,
                UserDeletion: true,
            },
        });

        expect(wrapper.find("#oidc-profile").exists()).toBe(false);
    });
});
