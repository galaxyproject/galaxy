import { createPinia } from "pinia";
import { shallowMount } from "@vue/test-utils";
import FavoritesButton from "./FavoritesButton";
import { useUserStore } from "stores/userStore";
import { getLocalVue } from "tests/jest/helpers";

const localVue = getLocalVue();

async function createWrapper(component, localVue, userData) {
    const pinia = createPinia();
    const wrapper = shallowMount(component, {
        localVue,
        pinia,
    });
    const userStore = useUserStore();
    userStore.currentUser = { ...userStore.currentUser, ...userData };
    return wrapper;
}

describe("Favorites Button", () => {
    it("describes it's function to logged-in users", async () => {
        const wrapper = await createWrapper(FavoritesButton, localVue, {
            id: "user.id",
            email: "user.email",
        });

        expect(wrapper.attributes("disabled")).toBeFalsy();
        expect(wrapper.attributes("title")).toBe("Show favorites");
    });

    it("prompts anonymous users to log in", async () => {
        const wrapper = await createWrapper(FavoritesButton, localVue, {});

        expect(wrapper.attributes("disabled")).toBeTruthy();
        expect(wrapper.attributes("title").toLowerCase()).toContain("log in");
    });
});
