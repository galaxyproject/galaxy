import { getLocalVue } from "@tests/jest/helpers";
import { shallowMount } from "@vue/test-utils";
import { createPinia } from "pinia";

import type { RegisteredUser } from "@/api";
import { useUserStore } from "@/stores/userStore";

import HistoryNavigation from "./HistoryNavigation.vue";

const localVue = getLocalVue();

async function createWrapper(propsData: object, userData?: Partial<RegisteredUser>) {
    const pinia = createPinia();

    const wrapper = shallowMount(HistoryNavigation as object, {
        propsData,
        localVue,
        pinia,
    });

    const userStore = useUserStore();
    userStore.currentUser = { ...(userStore.currentUser as RegisteredUser), ...userData };

    return wrapper;
}

describe("History Navigation", () => {
    it("presents all options to logged-in users", async () => {
        const wrapper = await createWrapper(
            {
                history: { id: "current_history_id" },
                histories: [],
            },
            {
                id: "user.id",
                email: "user.email",
            },
        );

        const createButton = wrapper.find("*[data-description='create new history']");
        expect(createButton.attributes().disabled).toBeFalsy();
        const switchButton = wrapper.find("*[data-description='switch to another history']");
        expect(switchButton.attributes().disabled).toBeFalsy();
    });

    it("disables options for anonymous users", async () => {
        const wrapper = await createWrapper({
            history: { id: "current_history_id" },
            histories: [],
        });

        const createButton = wrapper.find("*[data-description='create new history']");
        expect(createButton.attributes().disabled).toBeTruthy();
        const switchButton = wrapper.find("*[data-description='switch to another history']");
        expect(switchButton.attributes().disabled).toBeTruthy();
    });
});
