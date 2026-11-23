import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";

import type { RegisteredUser } from "@/api";
import { useUserStore } from "@/stores/userStore";

import ToolFilterChip from "./ToolFilterChip.vue";

const { showError } = vi.hoisted(() => ({ showError: vi.fn() }));
vi.mock("@/composables/toast", () => ({ useToast: () => ({ error: showError }) }));

const localVue = getLocalVue();
const cases = [
    ["tags", "data cleanup", "addFavoriteTag", "removeFavoriteTag"],
    ["edam_operations", "operation_1", "addFavoriteEdamOperation", "removeFavoriteEdamOperation"],
    ["edam_topics", "topic_1", "addFavoriteEdamTopic", "removeFavoriteEdamTopic"],
] as const;

function mountChip(kind: (typeof cases)[number][0], value: string, anonymous = false) {
    const pinia = createTestingPinia({ createSpy: vi.fn });
    const userStore = useUserStore(pinia);
    userStore.currentUser = (
        anonymous
            ? { id: "anonymous", isAnonymous: true }
            : { id: "user1", email: "user@example.org", isAnonymous: false }
    ) as RegisteredUser;
    userStore.currentPreferences = { favorites: { tools: [], tags: [], edam_operations: [], edam_topics: [] } };
    const wrapper = mount(ToolFilterChip, {
        localVue,
        pinia,
        props: { kind, value, label: "Selected filter", removeTitle: "Remove filter" },
    });
    return { wrapper, userStore };
}

describe("ToolFilterChip", () => {
    it.each(cases)("stars and unstars %s without removing the filter", async (kind, value, addAction, removeAction) => {
        const { wrapper, userStore } = mountChip(kind, value);
        const add = vi.spyOn(userStore, addAction).mockResolvedValue();
        const remove = vi.spyOn(userStore, removeAction).mockResolvedValue();
        const star = wrapper.get('button[title="Add Selected filter to Favorites"]');
        expect(star.attributes("aria-pressed")).toBe("false");
        await star.trigger("click");
        await flushPromises();
        expect(add).toHaveBeenCalledWith(value);
        expect(wrapper.emitted("remove")).toBeUndefined();

        userStore.currentPreferences!.favorites[kind] = [value];
        await flushPromises();
        const unstar = wrapper.get('button[title="Remove Selected filter from Favorites"]');
        expect(unstar.attributes("aria-pressed")).toBe("true");
        await unstar.trigger("click");
        await flushPromises();
        expect(remove).toHaveBeenCalledWith(value);
        await wrapper.get('button[title="Remove filter"]').trigger("click");
        expect(wrapper.emitted("remove")).toHaveLength(1);
    });

    it("disables the star for anonymous users while allowing filter removal", () => {
        const { wrapper } = mountChip("tags", "data cleanup", true);
        expect(wrapper.get('button[title="Sign in to manage favorites"]').attributes("aria-disabled")).toBeDefined();
        expect(wrapper.get('button[title="Remove filter"]').attributes("aria-disabled")).toBeUndefined();
    });

    it("prevents repeated saves and recovers after an error", async () => {
        const { wrapper, userStore } = mountChip("tags", "data cleanup");
        let rejectSave!: (error: Error) => void;
        vi.spyOn(userStore, "addFavoriteTag").mockImplementation(
            () =>
                new Promise((_, reject) => {
                    rejectSave = reject;
                }),
        );
        const star = wrapper.get('button[title="Add Selected filter to Favorites"]');
        await star.trigger("click");
        expect(star.attributes("aria-disabled")).toBeDefined();
        rejectSave(new Error("Failed"));
        await flushPromises();
        expect(showError).toHaveBeenCalledWith("Failed to update favorite 'Selected filter'.");
        expect(star.attributes("aria-disabled")).toBeUndefined();
        expect(wrapper.emitted("remove")).toBeUndefined();
    });
});
