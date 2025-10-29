import { mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { getLocalVue } from "tests/jest/helpers";

import { useUserStore } from "@/stores/userStore";

import DetailsLayout from "./DetailsLayout.vue";

const localVue = getLocalVue();

async function createWrapper(component, localVue, userData, unwritable = false) {
    const pinia = createPinia();
    const wrapper = mount(component, {
        localVue,
        pinia,
        propsData: {
            writeable: !unwritable,
            renameable: !unwritable,
        },
    });
    const userStore = useUserStore();
    userStore.currentUser = { ...userStore.currentUser, ...userData };
    return wrapper;
}

describe("DetailsLayout", () => {
    it("allows logged-in users to edit all details", async () => {
        const wrapper = await createWrapper(DetailsLayout, localVue, {
            id: "user.id",
            email: "user.email",
        });

        expect(wrapper.find(".edit-button").attributes("title")).toBe("Edit");

        // Click to edit and rename
        expect(wrapper.find(".click-to-edit-label").exists()).toBe(true);
    });

    it("prompts anonymous users to log in to edit all details, but allows rename", async () => {
        const wrapper = await createWrapper(DetailsLayout, localVue, {});

        expect(wrapper.find(".edit-button").attributes("title")).toContain("Log in");

        // Click to edit and rename should still be available
        expect(wrapper.find(".click-to-edit-label").exists()).toBe(true);
    });

    it("disallows editing and renaming if props set them to false", async () => {
        const wrapper = await createWrapper(
            DetailsLayout,
            localVue,
            {
                id: "user.id",
                email: "user.email",
            },
            true,
        );

        expect(wrapper.find(".edit-button").attributes("title")).toContain("Not Editable");
        expect(wrapper.find(".click-to-edit-label").exists()).toBe(false);
    });
});
