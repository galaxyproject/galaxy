import { mockModule, getLocalVue } from "tests/jest/helpers";
import { userStore } from "store/userStore";
import Vuex from "vuex";
import DetailsLayout from "./DetailsLayout";
import { mount } from "@vue/test-utils";

const localVue = getLocalVue();

const createStore = (currentUser) => {
    return new Vuex.Store({
        modules: {
            user: mockModule(userStore, { currentUser }),
        },
    });
};

describe("DetailsLayout", () => {
    it("allows logged-in users to edit details", () => {
        const store = createStore({
            id: "user.id",
            email: "user.email",
        });

        const wrapper = mount(DetailsLayout, {
            localVue,
            store,
            provide: { store },
        });

        expect(wrapper.find(".edit-button").attributes("title")).toBe("Edit");
    });

    it("prompts anonymous users to log in", () => {
        const store = createStore({});

        const wrapper = mount(DetailsLayout, {
            localVue,
            store,
            provide: { store },
        });

        expect(wrapper.find(".edit-button").attributes("title")).toContain("Log in");
    });
});
