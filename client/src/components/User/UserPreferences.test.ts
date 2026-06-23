import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import { faUnlockAlt } from "font-awesome-6";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { computed } from "vue";
import VueRouter from "vue-router";

import { hasSingleOidcProfile } from "@/components/User/ExternalIdentities/ExternalIDHelper";
import { getUserPreferencesModel } from "@/components/User/UserPreferencesModel";
import { useConfig } from "@/composables/config";

import UserPreferences from "./UserPreferences.vue";

vi.mock("@/composables/config", () => ({
    useConfig: vi.fn(),
}));

vi.mock("@/components/User/ExternalIdentities/ExternalIDHelper", () => ({
    hasSingleOidcProfile: vi.fn(),
}));

vi.mock("@/components/User/UserPreferencesModel", () => ({
    getUserPreferencesModel: vi.fn(),
}));

vi.mock("@/app", () => ({
    getGalaxyInstance: () => ({
        session_csrf_token: "mock-token",
    }),
}));

vi.mock("@/composables/confirmDialog", () => ({
    useConfirmDialog: () => ({
        confirm: vi.fn(),
    }),
}));

const localVue = getLocalVue();
localVue.use(VueRouter);

describe("UserPreferences.vue", () => {
    const mockPreferences = (passwordDisabled: boolean) => {
        // @ts-expect-error - getUserPreferencesModel is mocked
        vi.mocked(getUserPreferencesModel).mockReturnValue({
            password: {
                id: "edit-preferences-password",
                title: "Change Password",
                description: "Edit your password.",
                icon: faUnlockAlt,
                disabled: passwordDisabled,
                url: "/password",
                redirect: "/user",
            },
        });
    };

    beforeEach(() => {
        // Reset mocks
        mockPreferences(false);
    });

    it("shows oidc-profile element when OIDC is enabled and configured correctly", async () => {
        vi.mocked(useConfig).mockReturnValue({
            config: computed(() => ({
                enable_oidc: true,
                disable_local_accounts: true,
                oidc: {},
                themes: {},
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
                themes: {},
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

    it.each([
        [{ enable_account_interface: false }],
        [{ enable_account_interface: true, use_remote_user: true }],
        [{ enable_account_interface: true, disable_local_accounts: true }],
    ])("hides password preference when config is %o", async (configOverrides) => {
        // Mock the config returned by useConfig (used by the component for other things)
        vi.mocked(useConfig).mockReturnValue({
            config: computed(() => ({
                enable_oidc: false,
                disable_local_accounts: false,
                oidc: {},
                themes: {},
                ...configOverrides,
            })),
            isConfigLoaded: computed(() => true),
        });
        mockPreferences(true);

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

        expect(wrapper.find("#edit-preferences-password").exists()).toBe(false);
    });

    it("shows password preference when allowed", async () => {
        vi.mocked(useConfig).mockReturnValue({
            config: computed(() => ({
                disable_local_accounts: false,
                enable_account_interface: true,
                use_remote_user: false,
                themes: {},
            })),
            isConfigLoaded: computed(() => true),
        });
        mockPreferences(false);
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

        expect(wrapper.find("#edit-preferences-password").exists()).toBe(true);
    });
});
