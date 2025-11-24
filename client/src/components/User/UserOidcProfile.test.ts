import { createTestingPinia } from "@pinia/testing";
import { getFakeRegisteredUser } from "@tests/test-data";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import { useUserStore } from "@/stores/userStore";

import UserOidcProfile from "./UserOidcProfile.vue";

const PROFILE_URL = "https://profile.example.com";
const MOCK_CONFIG = {
    oidc_profile_url: PROFILE_URL,
    oidc: {
        provider: {
            label: "Example Provider",
        },
    },
};

vi.mock("@/composables/config", () => ({
    useConfig: vi.fn(() => ({
        config: ref(MOCK_CONFIG),
        isConfigLoaded: ref(true),
    })),
}));

vi.mock("@/components/Common/BreadcrumbHeading.vue", () => ({
    default: {
        name: "BreadcrumbHeading",
        props: ["items"],
        render() {
            return null;
        },
    },
}));

vi.mock("@/components/BaseComponents/GButton.vue", () => ({
    default: {
        name: "GButton",
        props: ["href"],
        render(h) {
            return h(
                "a",
                {
                    attrs: {
                        "data-test": "profile-link",
                        href: this.href,
                    },
                },
                this.$slots.default
            );
        },
    },
}));

const localVue = getLocalVue();

function mountProfile(userOverrides = {}) {
    const pinia = createTestingPinia({ createSpy: vi.fn });
    const userStore = useUserStore(pinia);
    userStore.currentUser = getFakeRegisteredUser(userOverrides);

    return mount(UserOidcProfile, {
        localVue,
        pinia,
        stubs: {
            FontAwesomeIcon: true,
        },
    });
}

describe("UserOidcProfile", () => {
    it("shows the profile link from config", async () => {
        const wrapper = mountProfile();
        await wrapper.vm.$nextTick();

        const profileButton = wrapper.findComponent({ name: "GButton" });
        expect(profileButton.exists()).toBe(true);
        expect(profileButton.props("href")).toBe(PROFILE_URL);
    });

    it("displays username and email from the user store", async () => {
        const username = "oidc_user";
        const email = "oidc_user@example.com";
        const wrapper = mountProfile({ username, email });
        await wrapper.vm.$nextTick();

        const details = wrapper.findAll("dd");
        expect(details.at(0)!.text()).toBe(email);
        expect(details.at(1)!.text()).toBe(username);
    });
});
