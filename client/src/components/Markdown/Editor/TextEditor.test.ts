import { composeStories } from "@storybook/vue3-vite";
import { emittedArg } from "@tests/vitest/helpers";
import { useStoryMount } from "@tests/vitest/stories";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useEventStore } from "@/stores/eventStore";

import * as TextEditorStories from "./TextEditor.stories";

import TextEditor from "./TextEditor.vue";

const stories = composeStories(TextEditorStories);
const mountStory = useStoryMount();
let eventStore: ReturnType<typeof useEventStore>;

async function mountEditor(props: Partial<InstanceType<typeof TextEditor>["$props"]> = {}) {
    const story =
        props.mode === "report"
            ? stories.WorkflowReportTemplate
            : props.hideToolbox === true
              ? stories.CompactPage
              : props.markdownText === "existing content"
                ? stories.PageWithExistingContent
                : stories.PageWithToolbox;
    const root = mountStory(story, {
        props,
        // These original cases cover the TextEditor's panel presence and drop contract.
        // Keep child stubs only here; standalone stories render the real toolbox/panel.
        global: {
            stubs: {
                MarkdownToolBox: { name: "MarkdownToolBox", template: "<div />" },
                FlexPanel: { name: "FlexPanel", template: "<div><slot /></div>" },
            },
        },
    });
    await vi.waitFor(() => root.getComponent(TextEditor));
    const wrapper = root.getComponent(TextEditor);
    eventStore = useEventStore();
    return wrapper;
}

type EditorWrapper = Awaited<ReturnType<typeof mountEditor>>;

function getTextarea(wrapper: EditorWrapper) {
    return wrapper.get<HTMLTextAreaElement>("textarea");
}

function makeDragEvent(type: string): Event {
    return new Event(type, { bubbles: true, cancelable: true });
}

function setDatasetDragItem(hid: number) {
    eventStore.setDragData({ hid, history_content_type: "dataset", id: "abc123", name: "test.txt" });
}

function setCollectionDragItem(hid: number) {
    eventStore.setDragData({ hid, history_content_type: "dataset_collection", id: "col123", name: "list" });
}

function setNonHistoryDragItem() {
    eventStore.setDragData({ id: "wf1", name: "workflow", hid: 1 });
}

async function dropAndGetUpdate(wrapper: EditorWrapper): Promise<unknown> {
    const textarea = getTextarea(wrapper);
    textarea.element.dispatchEvent(makeDragEvent("drop"));
    await wrapper.vm.$nextTick();
    const updates = wrapper.emitted("update");
    expect(updates).toBeTruthy();
    return emittedArg(wrapper, "update", -1);
}

async function applyHighlight(wrapper: EditorWrapper) {
    const textarea = getTextarea(wrapper);
    textarea.element.dispatchEvent(makeDragEvent("dragenter"));
    await wrapper.vm.$nextTick();
    expect(textarea.classes()).toContain("page-dragover-success");
}

beforeEach(() => {
    vi.clearAllMocks();
});

afterEach(() => {
    vi.restoreAllMocks();
});

describe("TextEditor toolbox visibility", () => {
    it("renders MarkdownToolBox when hideToolbox is not set", async () => {
        const wrapper = await mountEditor();
        expect(wrapper.findComponent({ name: "MarkdownToolBox" }).exists()).toBe(true);
        expect(wrapper.findComponent({ name: "FlexPanel" }).exists()).toBe(true);
    });

    it("renders MarkdownToolBox when hideToolbox is false", async () => {
        const wrapper = await mountEditor({ hideToolbox: false });
        expect(wrapper.findComponent({ name: "MarkdownToolBox" }).exists()).toBe(true);
        expect(wrapper.findComponent({ name: "FlexPanel" }).exists()).toBe(true);
    });

    it("hides MarkdownToolBox when hideToolbox is true", async () => {
        const wrapper = await mountEditor({ hideToolbox: true });
        expect(wrapper.findComponent({ name: "MarkdownToolBox" }).exists()).toBe(false);
        expect(wrapper.findComponent({ name: "FlexPanel" }).exists()).toBe(false);
    });
});

describe("TextEditor drag-and-drop", () => {
    describe("Drop insertion logic", () => {
        it("inserts history_dataset_display directive when dataset is dropped in page mode", async () => {
            const wrapper = await mountEditor({ markdownText: "existing content" });
            setDatasetDragItem(3);

            const content = await dropAndGetUpdate(wrapper);
            expect(content).toContain("history_dataset_display(history_dataset_id=abc123)");
            expect(content).toContain("```galaxy");
        });

        it("inserts history_dataset_collection_display directive when collection is dropped", async () => {
            const wrapper = await mountEditor({ markdownText: "" });
            setCollectionDragItem(5);

            const content = await dropAndGetUpdate(wrapper);
            expect(content).toContain("history_dataset_collection_display(history_dataset_collection_id=col123)");
        });

        it("does not insert anything when mode is 'report'", async () => {
            const wrapper = await mountEditor({ mode: "report" });
            setDatasetDragItem(3);

            const textarea = getTextarea(wrapper);
            textarea.element.dispatchEvent(makeDragEvent("drop"));
            await wrapper.vm.$nextTick();

            expect(wrapper.emitted("update")).toBeFalsy();
        });

        it("does not insert anything when eventStore has no drag data", async () => {
            const wrapper = await mountEditor();

            const textarea = getTextarea(wrapper);
            textarea.element.dispatchEvent(makeDragEvent("drop"));
            await wrapper.vm.$nextTick();

            expect(wrapper.emitted("update")).toBeFalsy();
        });

        it("does not insert anything when dragged item is not a history item", async () => {
            const wrapper = await mountEditor();
            setNonHistoryDragItem();

            const textarea = getTextarea(wrapper);
            textarea.element.dispatchEvent(makeDragEvent("drop"));
            await wrapper.vm.$nextTick();

            expect(wrapper.emitted("update")).toBeFalsy();
        });
    });

    describe("Visual feedback", () => {
        it("applies success highlight class on dragenter with valid item", async () => {
            const wrapper = await mountEditor();
            setDatasetDragItem(1);

            const textarea = getTextarea(wrapper);
            textarea.element.dispatchEvent(makeDragEvent("dragenter"));
            await wrapper.vm.$nextTick();

            expect(textarea.classes()).toContain("page-dragover-success");
        });

        it("does not apply highlight class on dragenter when mode is 'report'", async () => {
            const wrapper = await mountEditor({ mode: "report" });
            setDatasetDragItem(1);

            const textarea = getTextarea(wrapper);
            textarea.element.dispatchEvent(makeDragEvent("dragenter"));
            await wrapper.vm.$nextTick();

            expect(textarea.classes()).not.toContain("page-dragover-success");
        });

        it("removes highlight class on dragleave", async () => {
            const wrapper = await mountEditor();
            setDatasetDragItem(1);
            await applyHighlight(wrapper);

            const textarea = getTextarea(wrapper);
            textarea.element.dispatchEvent(makeDragEvent("dragleave"));
            await wrapper.vm.$nextTick();
            expect(textarea.classes()).not.toContain("page-dragover-success");
        });

        it("removes highlight class after drop", async () => {
            const wrapper = await mountEditor();
            setDatasetDragItem(1);
            await applyHighlight(wrapper);

            const textarea = getTextarea(wrapper);
            textarea.element.dispatchEvent(makeDragEvent("drop"));
            await wrapper.vm.$nextTick();
            expect(textarea.classes()).not.toContain("page-dragover-success");
        });
    });
});
