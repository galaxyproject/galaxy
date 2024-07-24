import { createTestingPinia } from "@pinia/testing";
import { mount, shallowMount } from "@vue/test-utils";
import { setActivePinia } from "pinia";
import { nextTick } from "vue";

import { type LazyUndoRedoAction, type UndoRedoAction } from "@/stores/undoRedoStore";
import { type TextWorkflowComment } from "@/stores/workflowEditorCommentStore";

import MarkdownComment from "./MarkdownComment.vue";
import TextComment from "./TextComment.vue";
import WorkflowComment from "./WorkflowComment.vue";

const changeData = jest.fn();
const changeSize = jest.fn();
const changePosition = jest.fn();
const changeColor = jest.fn();
const deleteComment = jest.fn();

const pinia = createTestingPinia();
setActivePinia(pinia);

jest.mock("@/composables/workflowStores", () => ({
    useWorkflowStores: () => ({
        commentStore: {
            changeData,
            changeSize,
            changePosition,
            changeColor,
            deleteComment,
            isJustCreated: () => false,
            getCommentMultiSelected: () => false,
        },
        undoRedoStore: {
            applyAction: (action: UndoRedoAction) => action.run(),
            applyLazyAction: (action: LazyUndoRedoAction) => {
                action.queued();
                action.run();
            },
        },
    }),
}));

function getStyleProperty(element: Element, property: string) {
    const style = element.getAttribute("style") ?? "";

    const startIndex = style.indexOf(`${property}:`) + property.length + 1;
    const endIndex = style.indexOf(";", startIndex);

    return style.substring(startIndex, endIndex).trim();
}

describe("WorkflowComment", () => {
    const comment = {
        id: 0,
        type: "text",
        color: "none",
        position: [0, 0],
        size: [100, 100],
        data: {},
    };

    it("changes position and size reactively", async () => {
        const wrapper = shallowMount(WorkflowComment as any, {
            propsData: {
                comment: { ...comment },
                scale: 1,
                rootOffset: {},
            },
        });

        const position = () => ({
            x: parseInt(getStyleProperty(wrapper.element, "--position-left")),
            y: parseInt(getStyleProperty(wrapper.element, "--position-top")),
        });

        const size = () => ({
            w: parseInt(getStyleProperty(wrapper.element, "--width")),
            h: parseInt(getStyleProperty(wrapper.element, "--height")),
        });

        expect(position()).toEqual({ x: 0, y: 0 });
        expect(size()).toEqual({ w: 100, h: 100 });

        await wrapper.setProps({
            comment: { ...comment, position: [123, 456] },
            scale: 1,
            rootOffset: {},
        });

        expect(position()).toEqual({ x: 123, y: 456 });
        expect(size()).toEqual({ w: 100, h: 100 });

        await wrapper.setProps({
            comment: { ...comment, size: [2000, 3000] },
            scale: 1,
            rootOffset: {},
        });

        expect(position()).toEqual({ x: 0, y: 0 });
        expect(size()).toEqual({ w: 2000, h: 3000 });
    });

    it("displays the correct comment type", async () => {
        const wrapper = mount(WorkflowComment as any, {
            propsData: {
                comment: { ...comment, type: "text", data: { size: 1, text: "HelloWorld" } },
                scale: 1,
                rootOffset: {},
            },
        });

        expect(wrapper.findComponent(TextComment).isVisible()).toBe(true);

        await wrapper.setProps({
            comment: { ...comment, type: "markdown", data: { text: "# Hello World" } },
            scale: 1,
            rootOffset: {},
        });

        await nextTick();
        expect(wrapper.findComponent(MarkdownComment).isVisible()).toBe(true);
    });

    it("forwards events to the comment store", () => {
        const testComment = { ...comment, id: 123, data: { size: 1, text: "HelloWorld" } } as TextWorkflowComment;

        const wrapper = mount(WorkflowComment as any, {
            propsData: {
                comment: testComment,
                scale: 1,
                rootOffset: {},
            },
        });

        const textComment = wrapper.findComponent(TextComment);

        textComment.vm.$emit("change", "abc");
        expect(changeData).toBeCalledWith(123, "abc");

        textComment.vm.$emit("resize", [1000, 1000]);
        expect(changeSize).toBeCalledWith(123, [1000, 1000]);

        textComment.vm.$emit("move", [20, 20]);
        expect(changePosition).toBeCalledWith(123, [20, 20]);

        textComment.vm.$emit("set-color", "pink");
        expect(changeColor).toBeCalledWith(123, "pink");

        textComment.vm.$emit("remove");
        expect(deleteComment).toBeCalledWith(123);
    });

    it("forwards pan events", () => {
        const wrapper = mount(WorkflowComment as any, {
            propsData: {
                comment: { ...comment, id: 123, data: { size: 1, text: "HelloWorld" } },
                scale: 1,
                rootOffset: {},
            },
        });

        const textComment = wrapper.findComponent(TextComment);

        textComment.vm.$emit("pan-by", { x: 50, y: 50 });
        expect(wrapper.emitted()["pan-by"]?.[0]?.[0]).toEqual({ x: 50, y: 50 });
    });
});
