import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { describe, expect, it } from "vitest";

import type { RegisteredUser } from "@/api";
import type GButton from "@/components/BaseComponents/GButton.vue";
import { useUserStore } from "@/stores/userStore";

import HistoryNavigation from "./HistoryNavigation.vue";

const localVue = getLocalVue();

async function createWrapper(props: object, userData?: Partial<RegisteredUser>) {
    const pinia = createPinia();

    const wrapper = shallowMount(HistoryNavigation as object, {
        props,
        global: localVue,
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

        const createButton = wrapper.findComponent<typeof GButton>("*[data-description='create new history']");
        expect(createButton.props("disabled")).toBe(false);
        const switchButton = wrapper.findComponent<typeof GButton>("*[data-description='switch to another history']");
        expect(switchButton.props("disabled")).toBe(false);
    });

    it("disables options for anonymous users", async () => {
        const wrapper = await createWrapper({
            history: { id: "current_history_id" },
            histories: [],
        });

        const createButton = wrapper.findComponent<typeof GButton>("*[data-description='create new history']");
        expect(createButton.props("disabled")).toBe(true);
        const switchButton = wrapper.findComponent<typeof GButton>("*[data-description='switch to another history']");
        expect(switchButton.props("disabled")).toBe(true);
    });
});
