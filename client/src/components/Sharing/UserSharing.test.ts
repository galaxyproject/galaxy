import { getFakeRegisteredUser } from "@tests/test-data";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick, ref } from "vue";
import Multiselect from "vue-multiselect";

import type { ShareableHistoryWithStatus } from "@/api";
import { useUserStore } from "@/stores/userStore";

import UserSharing from "./UserSharing.vue";
import GModal from "@/components/BaseComponents/GModal.vue";

vi.mock("axios");

vi.mock("@/composables/config", () => ({
    useConfig: vi.fn(() => ({
        config: ref({ expose_user_email: false }),
        isConfigLoaded: ref(true),
    })),
}));

const localVue = getLocalVue(true);

async function addCandidateEmail(wrapper: ReturnType<typeof mount>, email: string) {
    const multiselect = wrapper.findComponent(Multiselect);
    multiselect.vm.$emit("search-change", email);
    multiselect.vm.$emit("close");
    await nextTick();
}

function makeItem(overrides: Partial<ShareableHistoryWithStatus> = {}): ShareableHistoryWithStatus {
    return {
        id: "history_id",
        title: "My History",
        importable: false,
        published: false,
        users_shared_with: [],
        errors: [],
        extra: {
            can_change: [],
            cannot_change: [],
            can_share: true,
            accessible_count: 0,
        },
        ...overrides,
    };
}

async function mountComponent(item: ShareableHistoryWithStatus) {
    const pinia = createPinia();

    const wrapper = mount(UserSharing as object, {
        localVue,
        pinia,
        propsData: {
            item,
            modelClass: "History",
        },
    });

    const userStore = useUserStore();
    userStore.currentUser = getFakeRegisteredUser({ email: "owner@test.com", id: "owner_id" });

    await flushPromises();

    return wrapper;
}

describe("UserSharing.vue", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("does not show the permissions modal when no permission changes are required", async () => {
        const wrapper = await mountComponent(makeItem());

        expect(wrapper.findComponent(GModal).props("show")).toBe(false);
    });

    it("shows the permissions modal when the item requires permission changes", async () => {
        const item = makeItem({
            extra: {
                can_change: [{ id: "dataset_id", name: "A Dataset" }],
                cannot_change: [],
                can_share: false,
                accessible_count: 0,
            },
        });

        const wrapper = await mountComponent(item);

        expect(wrapper.findComponent(GModal).props("show")).toBe(true);
        expect(wrapper.text()).toContain("A Dataset");
    });

    it("emits share with the selected permission option when the modal is confirmed", async () => {
        const item = makeItem({
            extra: {
                can_change: [{ id: "dataset_id", name: "A Dataset" }],
                cannot_change: [],
                can_share: false,
                accessible_count: 0,
            },
        });

        const wrapper = await mountComponent(item);

        wrapper.findComponent(GModal).vm.$emit("ok");
        await flushPromises();

        expect(wrapper.emitted("share")).toBeTruthy();
        expect(wrapper.emitted("share")?.[0]).toEqual([[], "make_accessible_to_shared"]);
    });

    it("closes the permissions modal and emits cancel when the modal is cancelled", async () => {
        const item = makeItem({
            extra: {
                can_change: [{ id: "dataset_id", name: "A Dataset" }],
                cannot_change: [],
                can_share: false,
                accessible_count: 0,
            },
        });

        const wrapper = await mountComponent(item);

        expect(wrapper.findComponent(GModal).props("show")).toBe(true);

        wrapper.findComponent(GModal).vm.$emit("cancel");
        await flushPromises();

        expect(wrapper.findComponent(GModal).props("show")).toBe(false);
        expect(wrapper.emitted("cancel")).toBeTruthy();
    });

    it("emits share with the entered emails when Save is clicked", async () => {
        const item = makeItem({ users_shared_with: [{ email: "existing@test.com", id: "existing_id" }] });
        const wrapper = await mountComponent(item);

        await addCandidateEmail(wrapper, "new@test.com");

        const saveButton = wrapper.find("button.submit-sharing-with");
        await saveButton.trigger("click");

        expect(wrapper.emitted("share")).toBeTruthy();
        expect(wrapper.emitted("share")?.[0]).toEqual([["existing@test.com", "new@test.com"]]);
    });

    it("resets candidates to the current shared list and emits cancel when Cancel is clicked", async () => {
        const item = makeItem({ users_shared_with: [{ email: "existing@test.com", id: "existing_id" }] });
        const wrapper = await mountComponent(item);

        await addCandidateEmail(wrapper, "new@test.com");

        const cancelButton = wrapper.find("button.cancel-sharing-with");
        await cancelButton.trigger("click");

        expect(wrapper.emitted("cancel")).toBeTruthy();

        const saveButton = wrapper.find("button.submit-sharing-with");
        expect(saveButton.attributes("aria-disabled")).toBe("true");
    });
});
