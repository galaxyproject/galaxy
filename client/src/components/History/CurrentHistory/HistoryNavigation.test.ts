import { getFakeAnonymousUser, getFakeHistorySummary, getFakeRegisteredUser } from "@tests/test-data";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, shallowMount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { afterEach, describe, expect, it } from "vitest";

import type { AnonymousUser, RegisteredUser } from "@/api";
import { useUserStore } from "@/stores/userStore";

import HistoryNavigation from "./HistoryNavigation.vue";

enableAutoUnmount(afterEach);

function createWrapper(user: RegisteredUser | AnonymousUser) {
    const localVue = getLocalVue();
    const pinia = createPinia();
    useUserStore(pinia).currentUser = user;
    return shallowMount(HistoryNavigation, {
        props: { history: getFakeHistorySummary({ id: "current_history_id" }) },
        global: withPlugins(localVue, pinia),
    });
}

describe("History Navigation", () => {
    it("enables history creation and switching for logged-in users", () => {
        const wrapper = createWrapper(getFakeRegisteredUser({ id: "user.id", email: "user.email" }));
        const createButton = wrapper.get("[data-description='create new history']");
        const switchButton = wrapper.get("[data-description='switch to another history']");
        expect(createButton.attributes("disabled")).toBeUndefined();
        expect(switchButton.attributes("disabled")).toBeUndefined();
    });

    it("disables history creation and switching for anonymous users", () => {
        const wrapper = createWrapper(getFakeAnonymousUser());
        const createButton = wrapper.get("[data-description='create new history']");
        const switchButton = wrapper.get("[data-description='switch to another history']");
        expect(createButton.attributes("disabled")).toBeDefined();
        expect(switchButton.attributes("disabled")).toBeDefined();
    });
});
