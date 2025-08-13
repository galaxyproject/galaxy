import { shallowMount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { useUserStore } from "stores/userStore";
import { getLocalVue } from "tests/jest/helpers";

import FavoritesButton from "./FavoritesButton";

const globalConfig = getLocalVue();

async function createWrapper(component, globalConfig, userData) {
    const pinia = createPinia();
    const wrapper = shallowMount(component, {
        props: {
            query: "mock",
        },
        global: {
            ...globalConfig.global,
            plugins: [...(globalConfig.global?.plugins || []), pinia],
        },
    });
    const userStore = useUserStore();
    userStore.currentUser = { ...userStore.currentUser, ...userData };
    return wrapper;
}

describe("Favorites Button", () => {
    it("describes it's function to logged-in users", async () => {
        const wrapper = await createWrapper(FavoritesButton, globalConfig, {
            id: "user.id",
            email: "user.email",
        });

        expect(wrapper.attributes("disabled")).toBeFalsy();
        expect(wrapper.attributes("title")).toBe("Show favorites");
    });

    it("prompts anonymous users to log in", async () => {
        const wrapper = await createWrapper(FavoritesButton, globalConfig, {});

        expect(wrapper.attributes("disabled")).toBeTruthy();
        expect(wrapper.attributes("title").toLowerCase()).toContain("log in");
    });
});
