import { getFakeRegisteredUser } from "@tests/test-data";
import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";

import CopyModal from "./CopyModal.vue";
import GFormInput from "@/components/BaseComponents/Form/GFormInput.vue";
import GModal from "@/components/BaseComponents/GModal.vue";

const localVue = getLocalVue();

const fakeHistory = { id: "history_1", name: "My History" };
// history with an explicit owner id
const ownedHistory = { id: "history_1", name: "My History", user_id: "owner_id" };
const fakeOwner = getFakeRegisteredUser({ id: "owner_id" });
const otherUser = getFakeRegisteredUser({ id: "other_user" });

function createWrapper(history = fakeHistory as object, userData = fakeOwner, showModal = true) {
    const pinia = createPinia();
    const wrapper = shallowMount(CopyModal as object, {
        propsData: { history, showModal },
        localVue,
        pinia,
    });
    const userStore = useUserStore();
    userStore.currentUser = userData;
    const historyStore = useHistoryStore();
    vi.spyOn(historyStore, "copyHistory").mockResolvedValue(undefined);
    return { wrapper, historyStore };
}

describe("CopyModal", () => {
    beforeEach(() => vi.clearAllMocks());

    it("sets modal title from history name", () => {
        const { wrapper } = createWrapper();
        expect(wrapper.findComponent(GModal).props("title")).toBe("Copying History: My History");
    });

    it("pre-fills name input as \"Copy of 'history name'\"", () => {
        const { wrapper } = createWrapper();
        expect(wrapper.findComponent(GFormInput).props("value")).toBe("Copy of 'My History'");
    });

    it("updates name input when history prop changes", async () => {
        const { wrapper } = createWrapper();
        await wrapper.setProps({ history: { id: "h2", name: "Other History" } });
        expect(wrapper.findComponent(GFormInput).props("value")).toBe("Copy of 'Other History'");
    });

    it("ok button is disabled when name is empty", async () => {
        const { wrapper } = createWrapper();
        wrapper.findComponent(GFormInput).vm.$emit("input", "");
        await wrapper.vm.$nextTick();
        expect(wrapper.findComponent(GModal).props("okDisabled")).toBe(true);
    });

    it("ok button is disabled for owner when name matches history name", async () => {
        const { wrapper } = createWrapper(ownedHistory, fakeOwner);
        wrapper.findComponent(GFormInput).vm.$emit("input", ownedHistory.name);
        await wrapper.vm.$nextTick();
        expect(wrapper.findComponent(GModal).props("okDisabled")).toBe(true);
    });

    it("ok button is enabled for non-owner with same name as history", async () => {
        const { wrapper } = createWrapper(ownedHistory, otherUser);
        wrapper.findComponent(GFormInput).vm.$emit("input", ownedHistory.name);
        await wrapper.vm.$nextTick();
        expect(wrapper.findComponent(GModal).props("okDisabled")).toBe(false);
    });

    it("calls copyHistory with entered name and copyAll=false on ok", async () => {
        const { wrapper, historyStore } = createWrapper();
        wrapper.findComponent(GFormInput).vm.$emit("input", "New Name");
        await wrapper.vm.$nextTick();
        wrapper.findComponent(GModal).vm.$emit("ok");
        await flushPromises();
        expect(historyStore.copyHistory).toHaveBeenCalledWith(fakeHistory, "New Name", false);
    });

    it("emits update:show-modal false after copy completes", async () => {
        const { wrapper } = createWrapper();
        wrapper.findComponent(GFormInput).vm.$emit("input", "New Name");
        await wrapper.vm.$nextTick();
        wrapper.findComponent(GModal).vm.$emit("ok");
        await flushPromises();
        expect(wrapper.emitted()["update:show-modal"]?.at(-1)?.[0]).toBe(false);
    });
});
