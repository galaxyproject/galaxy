import { createTestingPinia } from "@pinia/testing";
import { getFakeRegisteredUser } from "@tests/test-data";
import { getLocalVue, nth, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { disposePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, onTestFinished, vi } from "vitest";
import { nextTick } from "vue";
import { createMemoryHistory, createRouter } from "vue-router";

import { resetMockConfig, setMockConfig } from "@/composables/__mocks__/config";
import { useUserStore } from "@/stores/userStore";

import UserOidcProfile from "./UserOidcProfile.vue";
import GButton from "@/components/BaseComponents/GButton.vue";

const PROFILE_URL = "https://profile.example.com";
const MOCK_CONFIG = {
    oidc: {
        provider: {
            label: "Example Provider",
            profile_url: PROFILE_URL,
        },
    },
};

vi.mock("@/composables/config");

beforeEach(() => {
    resetMockConfig();
    setMockConfig(MOCK_CONFIG);
});

afterEach(resetMockConfig);
enableAutoUnmount(afterEach);

const localVue = getLocalVue();

async function mountProfile(userOverrides: Parameters<typeof getFakeRegisteredUser>[0] = {}) {
    const pinia = createTestingPinia({ createSpy: vi.fn });
    onTestFinished(() => disposePinia(pinia));
    const userStore = useUserStore(pinia);
    userStore.currentUser = getFakeRegisteredUser(userOverrides);
    const router = createRouter({ history: createMemoryHistory(), routes: [] });

    const wrapper = mount(UserOidcProfile, {
        global: {
            ...withPlugins(localVue, pinia, router),
            stubs: { ...localVue.stubs, FontAwesomeIcon: true },
        },
    });
    await nextTick();
    return wrapper;
}

describe("UserOidcProfile", () => {
    it("shows the profile link from config", async () => {
        const wrapper = await mountProfile();

        const profileButton = wrapper.findComponent(GButton);
        expect(profileButton.exists()).toBe(true);
        expect(wrapper.getComponent(GButton).props("href")).toBe(PROFILE_URL);
    });

    it("displays username and email from the user store", async () => {
        const username = "oidc_user";
        const email = "oidc_user@example.com";
        const wrapper = await mountProfile({ username, email });

        const details = wrapper.findAll("dd");
        expect(nth(details, 0).text()).toBe(email);
        expect(nth(details, 1).text()).toBe(username);
    });
});
