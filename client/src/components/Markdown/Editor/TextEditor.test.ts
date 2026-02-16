import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount, type Wrapper } from "@vue/test-utils";
import type { Pinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type Vue from "vue";

import { useEventStore } from "@/stores/eventStore";

import TextEditor from "./TextEditor.vue";

vi.mock("@/components/Markdown/MarkdownToolBox.vue", () => ({
    default: {
        name: "MarkdownToolBox",
        template: "<div />",
    },
}));

vi.mock("@/components/Panels/FlexPanel.vue", () => ({
    default: {
        name: "FlexPanel",
        template: "<div><slot /></div>",
    },
}));

const localVue = getLocalVue();

let pinia: Pinia;
let eventStore: ReturnType<typeof useEventStore>;

function mountComponent(propsOverrides: Partial<{ markdownText: string; mode: string; title: string }> = {}) {
    return shallowMount(TextEditor as object, {
        localVue,
        propsData: {
            markdownText: "",
            mode: "page",
            title: "Test",
            ...propsOverrides,
        },
        pinia,
    });
}

function getTextarea(wrapper: Wrapper<Vue>) {
    return wrapper.find("textarea");
}

function makeDragEvent(type: string): DragEvent {
    const event = new Event(type, { bubbles: true, cancelable: true });
    return event as DragEvent;
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

async function dropAndGetUpdate(wrapper: Wrapper<Vue>): Promise<string> {
    const textarea = getTextarea(wrapper);
    textarea.element.dispatchEvent(makeDragEvent("drop"));
    await wrapper.vm.$nextTick();
    const updates = wrapper.emitted("update");
    expect(updates).toBeTruthy();
    return updates![updates!.length - 1]![0] as string;
}

async function applyHighlight(wrapper: Wrapper<Vue>) {
    const textarea = getTextarea(wrapper);
    textarea.element.dispatchEvent(makeDragEvent("dragenter"));
    await wrapper.vm.$nextTick();
    expect(textarea.classes()).toContain("page-dragover-success");
}

describe("TextEditor drag-and-drop", () => {
    beforeEach(() => {
        pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
        eventStore = useEventStore();
        vi.clearAllMocks();
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    describe("Drop insertion logic", () => {
        it("inserts history_dataset_display directive when dataset is dropped in page mode", async () => {
            const wrapper = mountComponent({ markdownText: "existing content" });
            setDatasetDragItem(3);

            const content = await dropAndGetUpdate(wrapper);
            expect(content).toContain("history_dataset_display(history_dataset_id=abc123)");
            expect(content).toContain("```galaxy");
        });

        it("inserts history_dataset_collection_display directive when collection is dropped", async () => {
            const wrapper = mountComponent({ markdownText: "" });
            setCollectionDragItem(5);

            const content = await dropAndGetUpdate(wrapper);
            expect(content).toContain("history_dataset_collection_display(history_dataset_collection_id=col123)");
        });

        it("does not insert anything when mode is 'report'", async () => {
            const wrapper = mountComponent({ mode: "report" });
            setDatasetDragItem(3);

            const textarea = getTextarea(wrapper);
            textarea.element.dispatchEvent(makeDragEvent("drop"));
            await wrapper.vm.$nextTick();

            expect(wrapper.emitted("update")).toBeFalsy();
        });

        it("does not insert anything when eventStore has no drag data", async () => {
            const wrapper = mountComponent();

            const textarea = getTextarea(wrapper);
            textarea.element.dispatchEvent(makeDragEvent("drop"));
            await wrapper.vm.$nextTick();

            expect(wrapper.emitted("update")).toBeFalsy();
        });

        it("does not insert anything when dragged item is not a history item", async () => {
            const wrapper = mountComponent();
            setNonHistoryDragItem();

            const textarea = getTextarea(wrapper);
            textarea.element.dispatchEvent(makeDragEvent("drop"));
            await wrapper.vm.$nextTick();

            expect(wrapper.emitted("update")).toBeFalsy();
        });
    });

    describe("Visual feedback", () => {
        it("applies success highlight class on dragenter with valid item", async () => {
            const wrapper = mountComponent();
            setDatasetDragItem(1);

            const textarea = getTextarea(wrapper);
            textarea.element.dispatchEvent(makeDragEvent("dragenter"));
            await wrapper.vm.$nextTick();

            expect(textarea.classes()).toContain("page-dragover-success");
        });

        it("does not apply highlight class on dragenter when mode is 'report'", async () => {
            const wrapper = mountComponent({ mode: "report" });
            setDatasetDragItem(1);

            const textarea = getTextarea(wrapper);
            textarea.element.dispatchEvent(makeDragEvent("dragenter"));
            await wrapper.vm.$nextTick();

            expect(textarea.classes()).not.toContain("page-dragover-success");
        });

        it("removes highlight class on dragleave", async () => {
            const wrapper = mountComponent();
            setDatasetDragItem(1);
            await applyHighlight(wrapper);

            const textarea = getTextarea(wrapper);
            textarea.element.dispatchEvent(makeDragEvent("dragleave"));
            await wrapper.vm.$nextTick();
            expect(textarea.classes()).not.toContain("page-dragover-success");
        });

        it("removes highlight class after drop", async () => {
            const wrapper = mountComponent();
            setDatasetDragItem(1);
            await applyHighlight(wrapper);

            const textarea = getTextarea(wrapper);
            textarea.element.dispatchEvent(makeDragEvent("drop"));
            await wrapper.vm.$nextTick();
            expect(textarea.classes()).not.toContain("page-dragover-success");
        });
    });
});
