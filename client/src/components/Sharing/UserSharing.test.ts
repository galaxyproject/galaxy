import { getFakeRegisteredUser } from "@tests/test-data";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount, type VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia } from "pinia";
import { afterEach, describe, expect, it, vi } from "vitest";
import { nextTick, ref } from "vue";
import Multiselect from "vue-multiselect";

import type { ShareableHistoryWithStatus } from "@/api";
import { useUserStore } from "@/stores/userStore";

import UserSharing from "./UserSharing.vue";
import GModal from "@/components/BaseComponents/GModal.vue";

vi.mock("@/composables/config", () => ({
    useConfig: vi.fn(() => ({
        config: ref({ expose_user_email: false }),
        isConfigLoaded: ref(true),
    })),
}));

const SELECTORS = {
    CANCEL_BUTTON: "button.cancel-sharing-with",
    MODAL_BUTTON: ".g-modal-confirm-buttons button",
    SAVE_BUTTON: "button.submit-sharing-with",
    SHARED_EMAIL_TAG: ".remove_sharing_with",
};

const localVue = getLocalVue();

enableAutoUnmount(afterEach);

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

function makeItemRequiringPermissionChanges() {
    return makeItem({
        extra: {
            can_change: [{ id: "dataset_id", name: "A Dataset" }],
            cannot_change: [],
            can_share: false,
            accessible_count: 0,
        },
    });
}

function makeItemSharedWithExistingUser() {
    return makeItem({ users_shared_with: [{ email: "existing@test.com", id: "existing_id" }] });
}

async function mountUserSharing(item: ShareableHistoryWithStatus) {
    const pinia = createPinia();
    useUserStore(pinia).currentUser = getFakeRegisteredUser({ email: "owner@test.com", id: "owner_id" });

    const wrapper = mount(UserSharing, {
        props: { item, modelClass: "History" },
        global: withPlugins(localVue, pinia),
    });
    await flushPromises();

    return wrapper;
}

async function addCandidateEmail(wrapper: VueWrapper, email: string) {
    const multiselect = wrapper.findComponent(Multiselect);
    multiselect.vm.$emit("search-change", email);
    multiselect.vm.$emit("close");
    await nextTick();
}

async function clickModalButton(wrapper: VueWrapper, text: "Ok" | "Cancel") {
    const button = wrapper.findAll(SELECTORS.MODAL_BUTTON).find((candidate) => candidate.text() === text);
    if (!button) {
        throw new Error(`no "${text}" button in the permissions modal`);
    }
    await button.trigger("click");
    await flushPromises();
}

function sharedEmailTags(wrapper: VueWrapper) {
    return wrapper.findAll(SELECTORS.SHARED_EMAIL_TAG).map((tag) => tag.attributes("data-email"));
}

describe("UserSharing", () => {
    describe("permissions modal", () => {
        it("stays closed when no permission changes are required", async () => {
            const wrapper = await mountUserSharing(makeItem());

            expect(wrapper.findComponent(GModal).props("show")).toBe(false);
        });

        it("opens and lists the datasets when the item requires permission changes", async () => {
            const wrapper = await mountUserSharing(makeItemRequiringPermissionChanges());

            expect(wrapper.findComponent(GModal).props("show")).toBe(true);
            expect(wrapper.text()).toContain("A Dataset");
        });

        it("emits share with the selected permission option when confirmed", async () => {
            const wrapper = await mountUserSharing(makeItemRequiringPermissionChanges());

            await clickModalButton(wrapper, "Ok");

            expect(wrapper.emitted("share")).toEqual([[[], "make_accessible_to_shared"]]);
            expect(wrapper.findComponent(GModal).props("show")).toBe(false);
        });

        it("closes and emits cancel when cancelled", async () => {
            const wrapper = await mountUserSharing(makeItemRequiringPermissionChanges());
            expect(wrapper.findComponent(GModal).props("show")).toBe(true);

            await clickModalButton(wrapper, "Cancel");

            expect(wrapper.findComponent(GModal).props("show")).toBe(false);
            expect(wrapper.emitted("cancel")).toEqual([[]]);
        });
    });

    describe("sharing with users", () => {
        it("emits share with the existing and entered emails when Save is clicked", async () => {
            const wrapper = await mountUserSharing(makeItemSharedWithExistingUser());
            await addCandidateEmail(wrapper, "new@test.com");

            await wrapper.find(SELECTORS.SAVE_BUTTON).trigger("click");

            expect(wrapper.emitted("share")).toEqual([[["existing@test.com", "new@test.com"]]]);
        });

        it("resets candidates to the current shared list and emits cancel when Cancel is clicked", async () => {
            const wrapper = await mountUserSharing(makeItemSharedWithExistingUser());
            await addCandidateEmail(wrapper, "new@test.com");
            expect(sharedEmailTags(wrapper)).toEqual(["existing@test.com", "new@test.com"]);

            await wrapper.find(SELECTORS.CANCEL_BUTTON).trigger("click");

            expect(wrapper.emitted("cancel")).toEqual([[]]);
            expect(sharedEmailTags(wrapper)).toEqual(["existing@test.com"]);
            expect(wrapper.find(SELECTORS.SAVE_BUTTON).attributes("aria-disabled")).toBe("true");
        });
    });
});
