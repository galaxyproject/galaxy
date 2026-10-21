import { createTestingPinia } from "@pinia/testing";
import { emittedArg, getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, shallowMount, type VueWrapper } from "@vue/test-utils";
import { disposePinia, type Pinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, onTestFinished, vi } from "vitest";

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

function mountEditor(props: Partial<InstanceType<typeof TextEditor>["$props"]> = {}) {
    return shallowMount(TextEditor, {
        global: withPlugins(localVue, pinia),
        props: {
            markdownText: "",
            mode: "page",
            title: "Test",
            ...props,
        },
    });
}

function getTextarea(wrapper: VueWrapper) {
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

async function dropAndGetUpdate(wrapper: VueWrapper): Promise<unknown> {
    const textarea = getTextarea(wrapper);
    textarea.element.dispatchEvent(makeDragEvent("drop"));
    await wrapper.vm.$nextTick();
    const updates = wrapper.emitted("update");
    expect(updates).toBeTruthy();
    return emittedArg(wrapper, "update", -1);
}

async function applyHighlight(wrapper: VueWrapper) {
    const textarea = getTextarea(wrapper);
    textarea.element.dispatchEvent(makeDragEvent("dragenter"));
    await wrapper.vm.$nextTick();
    expect(textarea.classes()).toContain("page-dragover-success");
}

beforeEach(() => {
    pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
    const ownedPinia = pinia;
    onTestFinished(() => disposePinia(ownedPinia));
    eventStore = useEventStore(pinia);
    vi.clearAllMocks();
});

afterEach(() => {
    vi.restoreAllMocks();
});
enableAutoUnmount(afterEach);

describe("TextEditor toolbox visibility", () => {
    it("renders MarkdownToolBox when hideToolbox is not set", () => {
        const wrapper = mountEditor();
        expect(wrapper.findComponent({ name: "MarkdownToolBox" }).exists()).toBe(true);
        expect(wrapper.findComponent({ name: "FlexPanel" }).exists()).toBe(true);
    });

    it("renders MarkdownToolBox when hideToolbox is false", () => {
        const wrapper = mountEditor({ hideToolbox: false });
        expect(wrapper.findComponent({ name: "MarkdownToolBox" }).exists()).toBe(true);
        expect(wrapper.findComponent({ name: "FlexPanel" }).exists()).toBe(true);
    });

    it("hides MarkdownToolBox when hideToolbox is true", () => {
        const wrapper = mountEditor({ hideToolbox: true });
        expect(wrapper.findComponent({ name: "MarkdownToolBox" }).exists()).toBe(false);
        expect(wrapper.findComponent({ name: "FlexPanel" }).exists()).toBe(false);
    });
});

describe("TextEditor drag-and-drop", () => {
    describe("Drop insertion logic", () => {
        it("inserts history_dataset_display directive when dataset is dropped in page mode", async () => {
            const wrapper = mountEditor({ markdownText: "existing content" });
            setDatasetDragItem(3);

            const content = await dropAndGetUpdate(wrapper);
            expect(content).toContain("history_dataset_display(history_dataset_id=abc123)");
            expect(content).toContain("```galaxy");
        });

        it("inserts history_dataset_collection_display directive when collection is dropped", async () => {
            const wrapper = mountEditor({ markdownText: "" });
            setCollectionDragItem(5);

            const content = await dropAndGetUpdate(wrapper);
            expect(content).toContain("history_dataset_collection_display(history_dataset_collection_id=col123)");
        });

        it("does not insert anything when mode is 'report'", async () => {
            const wrapper = mountEditor({ mode: "report" });
            setDatasetDragItem(3);

            const textarea = getTextarea(wrapper);
            textarea.element.dispatchEvent(makeDragEvent("drop"));
            await wrapper.vm.$nextTick();

            expect(wrapper.emitted("update")).toBeFalsy();
        });

        it("does not insert anything when eventStore has no drag data", async () => {
            const wrapper = mountEditor();

            const textarea = getTextarea(wrapper);
            textarea.element.dispatchEvent(makeDragEvent("drop"));
            await wrapper.vm.$nextTick();

            expect(wrapper.emitted("update")).toBeFalsy();
        });

        it("does not insert anything when dragged item is not a history item", async () => {
            const wrapper = mountEditor();
            setNonHistoryDragItem();

            const textarea = getTextarea(wrapper);
            textarea.element.dispatchEvent(makeDragEvent("drop"));
            await wrapper.vm.$nextTick();

            expect(wrapper.emitted("update")).toBeFalsy();
        });
    });

    describe("Visual feedback", () => {
        it("applies success highlight class on dragenter with valid item", async () => {
            const wrapper = mountEditor();
            setDatasetDragItem(1);

            const textarea = getTextarea(wrapper);
            textarea.element.dispatchEvent(makeDragEvent("dragenter"));
            await wrapper.vm.$nextTick();

            expect(textarea.classes()).toContain("page-dragover-success");
        });

        it("does not apply highlight class on dragenter when mode is 'report'", async () => {
            const wrapper = mountEditor({ mode: "report" });
            setDatasetDragItem(1);

            const textarea = getTextarea(wrapper);
            textarea.element.dispatchEvent(makeDragEvent("dragenter"));
            await wrapper.vm.$nextTick();

            expect(textarea.classes()).not.toContain("page-dragover-success");
        });

        it("removes highlight class on dragleave", async () => {
            const wrapper = mountEditor();
            setDatasetDragItem(1);
            await applyHighlight(wrapper);

            const textarea = getTextarea(wrapper);
            textarea.element.dispatchEvent(makeDragEvent("dragleave"));
            await wrapper.vm.$nextTick();
            expect(textarea.classes()).not.toContain("page-dragover-success");
        });

        it("removes highlight class after drop", async () => {
            const wrapper = mountEditor();
            setDatasetDragItem(1);
            await applyHighlight(wrapper);

            const textarea = getTextarea(wrapper);
            textarea.element.dispatchEvent(makeDragEvent("drop"));
            await wrapper.vm.$nextTick();
            expect(textarea.classes()).not.toContain("page-dragover-success");
        });
    });
});
