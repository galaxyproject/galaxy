import { mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { useUserStore } from "stores/userStore";
import { getLocalVue } from "tests/jest/helpers";

import DetailsLayout from "./DetailsLayout";

const localVue = getLocalVue();

async function createWrapper(component, localVue, userData) {
    const pinia = createPinia();
    const wrapper = mount(component, {
        localVue,
        pinia,
    });
    const userStore = useUserStore();
    userStore.currentUser = { ...userStore.currentUser, ...userData };
    return wrapper;
}

describe("DetailsLayout", () => {
    it("allows logged-in users to edit details", async () => {
        const wrapper = await createWrapper(DetailsLayout, localVue, {
            id: "user.id",
            email: "user.email",
        });

        expect(wrapper.find(".edit-button").attributes("title")).toBe("Edit");
    });

    it("prompts anonymous users to log in", async () => {
        const wrapper = await createWrapper(DetailsLayout, localVue, {});

        expect(wrapper.find(".edit-button").attributes("title")).toContain("Log in");
    });
});
