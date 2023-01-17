import { mockModule, getLocalVue } from "tests/jest/helpers";
import { userStore } from "store/userStore";
import Vuex from "vuex";
import FavoritesButton from "./FavoritesButton";
import { shallowMount } from "@vue/test-utils";

const localVue = getLocalVue();

const createStore = (currentUser) => {
    return new Vuex.Store({
        modules: {
            user: mockModule(userStore, { currentUser }),
        },
    });
};

describe("Favorites Button", () => {
    it("describes it's function to logged-in users", () => {
        const store = createStore({
            id: "user.id",
            email: "user.email",
        });

        const wrapper = shallowMount(FavoritesButton, {
            localVue,
            store,
            provide: { store },
        });

        expect(wrapper.attributes("disabled")).toBeFalsy();
        expect(wrapper.attributes("title")).toBe("Show favorites");
    });

    it("prompts anonymous users to log in", () => {
        const store = createStore({});

        const wrapper = shallowMount(FavoritesButton, {
            localVue,
            store,
            provide: { store },
        });

        expect(wrapper.attributes("disabled")).toBeTruthy();
        expect(wrapper.attributes("title").toLowerCase()).toContain("log in");
    });
});
