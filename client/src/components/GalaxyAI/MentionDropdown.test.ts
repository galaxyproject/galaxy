import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import MentionDropdown from "./MentionDropdown.vue";

vi.mock("@/stores/historyStore", () => ({
    useHistoryStore: () => ({ currentHistoryId: null, currentHistory: null }),
}));
vi.mock("@/stores/historyItemsStore", () => ({
    useHistoryItemsStore: () => ({ getHistoryItems: () => [] }),
}));

describe("MentionDropdown", () => {
    // Unselected options need aria-selected="false", not a missing attribute
    it("marks every option with an explicit aria-selected string", async () => {
        const wrapper = mount(MentionDropdown as any, {
            props: { visible: true, mentionType: null, searchText: "", anchorEl: null },
        });
        const options = wrapper.findAll("[role='option']");
        expect(options.map((option) => option.attributes("aria-selected"))).toEqual(["true", "false"]);

        await options[1]!.trigger("mouseenter");
        expect(options.map((option) => option.attributes("aria-selected"))).toEqual(["false", "true"]);
        wrapper.unmount();
    });
});
