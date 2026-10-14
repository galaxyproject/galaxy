import { createTestingPinia } from "@pinia/testing";
import { composeStories } from "@storybook/vue3-vite";
import { emittedArg, nth, suppressErrorForCustomIcons } from "@tests/vitest/helpers";
import { type StoryOf, useStoryMount } from "@tests/vitest/stories";
import { mount, shallowMount } from "@vue/test-utils";
import { zoomIdentity } from "d3-zoom";
import { afterEach, beforeEach, describe, expect, it, onTestFinished, vi } from "vitest";
import { nextTick, ref } from "vue";

import { sanitizeHtml } from "@/directives/sanitizeHtml";
import {
    type MarkdownWorkflowComment,
    type TextWorkflowComment,
    useWorkflowCommentStore,
    type WorkflowComment as WorkflowCommentModel,
} from "@/stores/workflowEditorCommentStore";

import { COMMENTS_WORKFLOW_ID } from "./test_fixtures";
import * as WorkflowCommentStories from "./WorkflowComment.stories";

import MarkdownComment from "./MarkdownComment.vue";
import TextComment from "./TextComment.vue";
import WorkflowComment from "./WorkflowComment.vue";

const stories = composeStories(WorkflowCommentStories);
const mountStory = useStoryMount();

const TEXT_NOTE = stories.TextNote.args.comment as TextWorkflowComment;
const MARKDOWN_NOTE = stories.MarkdownNote.args.comment as MarkdownWorkflowComment;

const sanitizeMock = vi.mocked(sanitizeHtml);
const originalSanitize = sanitizeMock.getMockImplementation();

afterEach(() => {
    sanitizeMock.mockReset();
    if (originalSanitize) {
        sanitizeMock.mockImplementation(originalSanitize);
    }
    vi.restoreAllMocks();
});
afterEach(async () => {
    // Let the mounted draggable's current resize/frame callbacks finish before unmount.
    await new Promise((resolve) => window.requestAnimationFrame(resolve));
});

/** WorkflowComment on its own, for checks that change its props on a live mount (a story remounts on setProps). */
function mountLiveComment(mountComponent: typeof mount | typeof shallowMount, comment: WorkflowCommentModel) {
    const wrapper = mountComponent(WorkflowComment, {
        props: { ...WorkflowCommentStories.default.args, comment },
        global: {
            plugins: [createTestingPinia({ createSpy: vi.fn })],
            provide: { workflowId: COMMENTS_WORKFLOW_ID, transform: ref(zoomIdentity) },
        },
    });
    onTestFinished(() => wrapper.unmount());
    return wrapper;
}

function getStyleProperty(element: Element, property: string) {
    const style = element.getAttribute("style") ?? "";

    const startIndex = style.indexOf(`${property}:`) + property.length + 1;
    const endIndex = style.indexOf(";", startIndex);

    return style.substring(startIndex, endIndex).trim();
}

describe("WorkflowComment", () => {
    beforeEach(() => {
        suppressErrorForCustomIcons();
    });

    it("changes position and size reactively", async () => {
        const wrapper = mountLiveComment(shallowMount, TEXT_NOTE);

        const position = () => ({
            x: parseInt(getStyleProperty(wrapper.element, "--position-left")),
            y: parseInt(getStyleProperty(wrapper.element, "--position-top")),
        });

        const size = () => ({
            w: parseInt(getStyleProperty(wrapper.element, "--width")),
            h: parseInt(getStyleProperty(wrapper.element, "--height")),
        });

        const [x, y] = TEXT_NOTE.position;
        const [w, h] = TEXT_NOTE.size;
        expect(position()).toEqual({ x, y });
        expect(size()).toEqual({ w, h });

        await wrapper.setProps({ comment: { ...TEXT_NOTE, position: [123, 456] } });

        expect(position()).toEqual({ x: 123, y: 456 });
        expect(size()).toEqual({ w, h });

        await wrapper.setProps({ comment: { ...TEXT_NOTE, size: [2000, 3000] } });

        expect(position()).toEqual({ x, y });
        expect(size()).toEqual({ w: 2000, h: 3000 });
    });

    it("displays the correct comment type", () => {
        expect(mountStory(stories.TextNote).getComponent(TextComment).isVisible()).toBe(true);
        expect(mountStory(stories.MarkdownNote).getComponent(MarkdownComment).isVisible()).toBe(true);
    });

    it("displays the new comment type after a live change", async () => {
        const wrapper = mountLiveComment(mount, TEXT_NOTE);

        expect(wrapper.getComponent(TextComment).isVisible()).toBe(true);

        await wrapper.setProps({ comment: MARKDOWN_NOTE });

        await nextTick();
        expect(wrapper.getComponent(MarkdownComment).isVisible()).toBe(true);
    });

    it("forwards events to the comment store", () => {
        const { id } = TEXT_NOTE;
        const textComment = mountStory(stories.TextNote).getComponent(TextComment);
        const commentStore = useWorkflowCommentStore(COMMENTS_WORKFLOW_ID);
        const editedData = { size: 1, text: "Trim adapters before mapping" };

        textComment.vm.$emit("change", editedData);
        expect(commentStore.changeData).toBeCalledWith(id, editedData);

        textComment.vm.$emit("resize", [1000, 1000]);
        expect(commentStore.changeSize).toBeCalledWith(id, [1000, 1000]);

        textComment.vm.$emit("move", [20, 20]);
        expect(commentStore.changePosition).toBeCalledWith(id, [20, 20]);

        textComment.vm.$emit("set-color", "pink");
        expect(commentStore.changeColor).toBeCalledWith(id, "pink");

        textComment.vm.$emit("remove");
        expect(commentStore.deleteComment).toBeCalledWith(id);
    });

    it("forwards pan events", () => {
        const wrapper = mountStory(stories.TextNote);

        wrapper.getComponent(TextComment).vm.$emit("pan-by", { x: 50, y: 50 });
        expect(emittedArg(wrapper.getComponent(WorkflowComment), "pan-by")).toEqual({ x: 50, y: 50 });
    });

    describe("rendering comment text", () => {
        function mountComment(story: StoryOf<typeof stories>) {
            vi.mocked(sanitizeHtml).mockClear();
            vi.mocked(sanitizeHtml).mockImplementation((html) => `<span class="sanitized">${html}</span>`);
            return mountStory(story);
        }

        it("renders text comments through v-sanitize-html", () => {
            const wrapper = mountComment(stories.TextNote);
            // escapeAndSanitize runs DOMPurify first, whose happy-dom output isn't meaningful
            expect(sanitizeHtml).toHaveBeenCalledWith(expect.any(String), "default");
            expect(wrapper.find(".sanitized").exists()).toBe(true);
        });

        it("renders frame titles through v-sanitize-html", () => {
            const wrapper = mountComment(stories.ColoredFrame);
            expect(sanitizeHtml).toHaveBeenCalledWith(expect.any(String), "default");
            expect(wrapper.find(".sanitized").exists()).toBe(true);
        });

        it("renders markdown comments with the links profile", () => {
            const wrapper = mountComment(stories.MarkdownNote);
            const [html, profile] = nth(sanitizeMock.mock.calls, 0);
            expect(profile).toBe("links");
            expect(html).toContain('target="_blank"');
            // markdown-it escapes raw HTML in the source before it reaches the sanitizer
            expect(html).toContain("&lt;b&gt;before&lt;/b&gt;");
            expect(wrapper.find(".rendered-markdown .sanitized").exists()).toBe(true);
        });
    });
});
