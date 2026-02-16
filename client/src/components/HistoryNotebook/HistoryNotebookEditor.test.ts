import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount, type Wrapper } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import HistoryNotebookEditor from "./HistoryNotebookEditor.vue";
import MarkdownEditor from "@/components/Markdown/MarkdownEditor.vue";

const HISTORY_ID = "history-1";
const MISSING_HISTORY_ID = "history-unknown";
const HISTORY_NAME = "Test History";
const CONTENT = "# Hello\nSome notebook content";

const mockGetHistoryById = vi.fn((id: string) => {
    if (id === HISTORY_ID) {
        return { id: HISTORY_ID, name: HISTORY_NAME };
    }
    return undefined;
});

vi.mock("@/stores/historyStore", () => ({
    useHistoryStore: vi.fn(() => ({
        getHistoryById: mockGetHistoryById,
    })),
}));

const localVue = getLocalVue();

function mountComponent(propsData: { historyId: string; content: string }) {
    return shallowMount(HistoryNotebookEditor as object, {
        localVue,
        propsData,
    });
}

describe("HistoryNotebookEditor", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    describe("Props passing to MarkdownEditor", () => {
        let wrapper: Wrapper<Vue>;

        beforeEach(() => {
            wrapper = mountComponent({ historyId: HISTORY_ID, content: CONTENT });
        });

        it("passes content prop as markdown-text to MarkdownEditor", () => {
            const editor = wrapper.findComponent(MarkdownEditor);
            expect(editor.props("markdownText")).toBe(CONTENT);
        });

        it("passes 'history_notebook' as mode to MarkdownEditor", () => {
            const editor = wrapper.findComponent(MarkdownEditor);
            expect(editor.props("mode")).toBe("history_notebook");
        });

        it("passes history name as title to MarkdownEditor", () => {
            const editor = wrapper.findComponent(MarkdownEditor);
            expect(editor.props("title")).toBe(HISTORY_NAME);
        });
    });

    describe("Computed title fallback", () => {
        it("falls back to 'History Notebook' when history not found in store", () => {
            const wrapper = mountComponent({ historyId: MISSING_HISTORY_ID, content: CONTENT });
            const editor = wrapper.findComponent(MarkdownEditor);
            expect(editor.props("title")).toBe("History Notebook");
        });
    });

    describe("Event propagation", () => {
        it("emits 'update:content' when MarkdownEditor emits 'update'", async () => {
            const wrapper = mountComponent({ historyId: HISTORY_ID, content: CONTENT });
            const editor = wrapper.findComponent(MarkdownEditor);
            const newContent = "# Updated content";
            editor.vm.$emit("update", newContent);
            await wrapper.vm.$nextTick();
            expect(wrapper.emitted()["update:content"]).toBeTruthy();
            expect(wrapper.emitted()["update:content"]![0]![0]).toBe(newContent);
        });
    });
});
