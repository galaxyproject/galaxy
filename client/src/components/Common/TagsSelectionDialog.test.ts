import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

import TagsSelectionDialog from "./TagsSelectionDialog.vue";

vi.mock("@/stores/userTagsStore", () => ({
    useUserTagsStore: vi.fn(() => ({
        userTags: [],
        onNewTagSeen: vi.fn(),
        onTagUsed: vi.fn(),
        onMultipleNewTagsSeen: vi.fn(),
    })),
    normalizeTag: vi.fn((tag: string) => tag),
}));

describe("TagsSelectionDialog", () => {
    it("shows the tag suggestions inside the dialog body, under a full-width tag input", async () => {
        const wrapper = mount(TagsSelectionDialog, {
            props: { show: true, initialTags: ["abc"] },
            global: getLocalVue(),
            attachTo: document.body,
        });

        expect(wrapper.find(".stateless-tags .tags-edit").classes()).not.toContain("d-flex");

        await wrapper.find(".stateless-tags .toggle-button").trigger("click");
        await nextTick();

        expect(wrapper.find(".stateless-tags input[role='combobox']").exists()).toBe(true);
        expect(wrapper.find(".stateless-tags [role='listbox']").exists()).toBe(true);
        wrapper.unmount();
    });
});
