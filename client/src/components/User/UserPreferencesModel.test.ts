import { createTestingPinia } from "@pinia/testing";
import { setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { computed } from "vue";

import { getUserPreferencesModel } from "@/components/User/UserPreferencesModel";
import { useConfig } from "@/composables/config";

vi.mock("@/composables/config", () => ({
    useConfig: vi.fn(),
}));

const mockConfig = (cfg: any) =>
    vi.mocked(useConfig).mockReturnValue({
        config: computed(() => cfg),
        isConfigLoaded: computed(() => true),
    });

describe("getUserPreferencesModel", () => {
    beforeEach(() => {
        setActivePinia(createTestingPinia({ createSpy: vi.fn }));
    });

    it("disables password when account interface is off", () => {
        mockConfig({
            enable_account_interface: false,
            use_remote_user: false,
            disable_local_accounts: false,
            has_user_tool_filters: false,
            themes: {},
        });

        const prefs = getUserPreferencesModel("user-id");
        expect(prefs.password.disabled).toBe(true);
    });

    it("disables password when using remote user", () => {
        mockConfig({
            enable_account_interface: true,
            use_remote_user: true,
            disable_local_accounts: false,
            has_user_tool_filters: false,
            themes: {},
        });

        const prefs = getUserPreferencesModel("user-id");
        expect(prefs.password.disabled).toBe(true);
    });

    it("enables password when local accounts allowed and interface enabled", () => {
        mockConfig({
            enable_account_interface: true,
            use_remote_user: false,
            disable_local_accounts: false,
            has_user_tool_filters: false,
            themes: {},
        });

        const prefs = getUserPreferencesModel("user-id");
        expect(prefs.password.disabled).toBe(false);
    });
});
