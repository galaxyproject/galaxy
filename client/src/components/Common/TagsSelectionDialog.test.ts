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
    it("shows the tag suggestions in the dialog body, under the tag input", async () => {
        const wrapper = mount(TagsSelectionDialog, {
            props: { show: true, initialTags: ["abc"] },
            global: getLocalVue(),
            attachTo: document.body,
        });

        await wrapper.find(".stateless-tags .toggle-button").trigger("click");
        await nextTick();

        const dialogBody = wrapper.find("dialog .g-modal-content").element;
        const input = document.querySelector("input[role='combobox']") as Element;
        const listbox = document.querySelector("[role='listbox']") as Element;
        expect(listbox).not.toBeNull();
        expect(dialogBody.contains(listbox)).toBe(true);
        expect(dialogBody.contains(input)).toBe(true);
        expect(input.compareDocumentPosition(listbox) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
        wrapper.unmount();
    });
});
