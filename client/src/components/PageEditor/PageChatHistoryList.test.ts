import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import PageChatHistoryList from "./PageChatHistoryList.vue";

const MOCK_ITEMS = [
    {
        id: "enc1",
        query: "First question",
        response: "First answer",
        agent_type: "page_assistant",
        timestamp: "2025-06-15T10:00:00Z",
        feedback: null,
        message_count: 2,
    },
    {
        id: "enc2",
        query: "Second question",
        response: "Second answer",
        agent_type: "page_assistant",
        timestamp: "2025-06-14T09:00:00Z",
        feedback: 1,
        message_count: 4,
    },
    {
        id: "enc3",
        query: "Third question",
        response: "Third answer",
        agent_type: "page_assistant",
        timestamp: "2025-06-13T08:00:00Z",
        feedback: null,
        message_count: 2,
    },
];

function mountList(props: Record<string, unknown> = {}) {
    return mount(PageChatHistoryList as any, {
        propsData: {
            items: MOCK_ITEMS,
            isLoading: false,
            error: null,
            activeExchangeId: null,
            ...props,
        },
        stubs: {
            FontAwesomeIcon: true,
            UtcDate: true,
            BAlert: true,
        },
    });
}

describe("PageChatHistoryList", () => {
    // Vue 2.7 emits prop warnings for `string | null` TS types; suppress them
    beforeEach(() => {
        vi.spyOn(console, "error").mockImplementation(() => {});
    });
    describe("rendering", () => {
        it("renders items", () => {
            const wrapper = mountList();
            const items = wrapper.findAll('[data-description="sidebar item"]');
            expect(items.length).toBe(3);
        });

        it("shows query text for each item", () => {
            const wrapper = mountList();
            expect(wrapper.text()).toContain("First question");
            expect(wrapper.text()).toContain("Second question");
            expect(wrapper.text()).toContain("Third question");
        });

        it("shows empty message when no items", () => {
            const wrapper = mountList({ items: [] });
            expect(wrapper.text()).toContain("No conversations yet.");
        });

        it("shows loading message when loading", () => {
            const wrapper = mountList({ isLoading: true });
            expect(wrapper.text()).toContain("Loading history...");
        });
    });

    describe("selection mode toggle", () => {
        it("trash button toggles selection mode on", async () => {
            const wrapper = mountList();
            expect(wrapper.find(".selection-toolbar").exists()).toBe(false);

            await wrapper.find('[data-description="toggle selection button"]').trigger("click");

            expect(wrapper.find(".selection-toolbar").exists()).toBe(true);
        });

        it("cancel button toggles selection mode off", async () => {
            const wrapper = mountList();
            await wrapper.find('[data-description="toggle selection button"]').trigger("click");
            expect(wrapper.find(".selection-toolbar").exists()).toBe(true);

            await wrapper.find('[data-description="toggle selection button"]').trigger("click");

            expect(wrapper.find(".selection-toolbar").exists()).toBe(false);
        });

        it("checkboxes visible in selection mode", async () => {
            const wrapper = mountList();
            expect(wrapper.find(".history-checkbox").exists()).toBe(false);

            await wrapper.find('[data-description="toggle selection button"]').trigger("click");

            expect(wrapper.findAll(".history-checkbox").length).toBe(3);
        });
    });

    describe("item clicks", () => {
        it("emits select when clicking item outside selection mode", async () => {
            const wrapper = mountList();
            await wrapper.findAll('[data-description="sidebar item"]').at(0)!.trigger("click");

            const emitted = wrapper.emitted("select");
            expect(emitted).toBeTruthy();
            expect(emitted![0]![0]).toEqual(MOCK_ITEMS[0]);
        });

        it("does NOT emit select when clicking item in selection mode", async () => {
            const wrapper = mountList();
            await wrapper.find('[data-description="toggle selection button"]').trigger("click");

            await wrapper.findAll('[data-description="sidebar item"]').at(0)!.trigger("click");

            expect(wrapper.emitted("select")).toBeFalsy();
        });

        it("toggles item selection when clicking in selection mode", async () => {
            const wrapper = mountList();
            await wrapper.find('[data-description="toggle selection button"]').trigger("click");

            await wrapper.findAll('[data-description="sidebar item"]').at(1)!.trigger("click");

            // Delete button should show count
            const deleteBtn = wrapper.find('[data-description="delete selected button"]');
            expect(deleteBtn.text()).toContain("1");
        });
    });

    describe("select all / deselect all", () => {
        it("select all selects all items", async () => {
            const wrapper = mountList();
            await wrapper.find('[data-description="toggle selection button"]').trigger("click");

            await wrapper.find(".select-all-toggle").trigger("click");

            const deleteBtn = wrapper.find('[data-description="delete selected button"]');
            expect(deleteBtn.text()).toContain("3");
        });

        it("deselect all clears selection", async () => {
            const wrapper = mountList();
            await wrapper.find('[data-description="toggle selection button"]').trigger("click");
            // Select all
            await wrapper.find(".select-all-toggle").trigger("click");
            // Deselect all
            await wrapper.find(".select-all-toggle").trigger("click");

            const deleteBtn = wrapper.find('[data-description="delete selected button"]');
            expect((deleteBtn.element as HTMLButtonElement).disabled).toBe(true);
        });
    });

    describe("delete", () => {
        it("delete button disabled when nothing selected", async () => {
            const wrapper = mountList();
            await wrapper.find('[data-description="toggle selection button"]').trigger("click");

            const deleteBtn = wrapper.find('[data-description="delete selected button"]');
            expect((deleteBtn.element as HTMLButtonElement).disabled).toBe(true);
        });

        it("delete button emits delete with selected IDs", async () => {
            const wrapper = mountList();
            await wrapper.find('[data-description="toggle selection button"]').trigger("click");

            // Click first and third items
            const items = wrapper.findAll('[data-description="sidebar item"]');
            await items.at(0)!.trigger("click");
            await items.at(2)!.trigger("click");

            await wrapper.find('[data-description="delete selected button"]').trigger("click");

            const emitted = wrapper.emitted("delete");
            expect(emitted).toBeTruthy();
            const ids = emitted![0]![0] as string[];
            expect(ids).toHaveLength(2);
            expect(ids).toContain("enc1");
            expect(ids).toContain("enc3");
        });
    });

    describe("shift-click range selection", () => {
        it("selects range with shift-click", async () => {
            const wrapper = mountList();
            await wrapper.find('[data-description="toggle selection button"]').trigger("click");

            const items = wrapper.findAll('[data-description="sidebar item"]');
            // Click first item normally
            await items.at(0)!.trigger("click");
            // Shift-click third item
            await items.at(2)!.trigger("click", { shiftKey: true });

            // All 3 should be selected
            const deleteBtn = wrapper.find('[data-description="delete selected button"]');
            expect(deleteBtn.text()).toContain("3");
        });
    });

    describe("active exchange highlight", () => {
        it("applies active class to matching item when not in selection mode", () => {
            const wrapper = mountList({ activeExchangeId: "enc2" });
            const items = wrapper.findAll('[data-description="sidebar item"]');
            expect(items.at(1)!.classes()).toContain("active");
        });

        it("does not apply active class in selection mode", async () => {
            const wrapper = mountList({ activeExchangeId: "enc2" });
            await wrapper.find('[data-description="toggle selection button"]').trigger("click");

            const items = wrapper.findAll('[data-description="sidebar item"]');
            expect(items.at(1)!.classes()).not.toContain("active");
        });
    });
});
