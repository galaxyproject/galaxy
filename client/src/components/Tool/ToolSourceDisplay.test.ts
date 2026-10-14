import { composeStories } from "@storybook/vue3-vite";
import { useStoryMount } from "@tests/vitest/stories";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as ToolSourceDisplayStories from "./ToolSourceDisplay.stories";

import ToolSourceDisplay from "./ToolSourceDisplay.vue";

const stories = composeStories(ToolSourceDisplayStories);
const mountStory = useStoryMount();

const { mockEditor, mockModel, mockMonaco } = vi.hoisted(() => {
    const mockModel = {};
    const mockEditor = {
        dispose: vi.fn(),
        getModel: vi.fn(() => mockModel),
        setValue: vi.fn(),
    };
    const mockMonaco = {
        editor: {
            create: vi.fn(() => mockEditor),
            setModelLanguage: vi.fn(),
        },
    };
    return { mockEditor, mockModel, mockMonaco };
});

vi.mock("@monaco-editor/loader", () => ({
    default: { init: vi.fn(() => Promise.resolve(mockMonaco)), config: vi.fn() },
}));
vi.mock("monaco-editor/esm/vs/editor/editor.main.js", () => mockMonaco);
vi.mock("monaco-editor/esm/vs/editor/editor.worker?worker", () => ({ default: vi.fn() }));

afterEach(() => {
    vi.clearAllMocks();
});
enableAutoUnmount(afterEach);

async function mountToolSourceDisplay() {
    const wrapper = mount(ToolSourceDisplay, {
        props: { code: "<tool id='cat1'/>", language: "xml" },
    });
    await flushPromises();
    return wrapper;
}

async function mountToolSourceStory() {
    const wrapper = mountStory(stories.XmlToolSource);
    await vi.waitFor(() => expect(mockMonaco.editor.create).toHaveBeenCalled());
    return wrapper;
}

describe("ToolSourceDisplay", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("creates a read-only editor in its container", async () => {
        const wrapper = await mountToolSourceStory();
        expect(mockMonaco.editor.create).toHaveBeenCalledTimes(1);
        expect(mockMonaco.editor.create).toHaveBeenCalledWith(
            wrapper.get(".editor-container").element,
            expect.objectContaining({ value: stories.XmlToolSource.args.code, language: "xml", readOnly: true }),
        );
    });

    it("updates the editor when the code changes", async () => {
        const wrapper = await mountToolSourceDisplay();
        await wrapper.setProps({ code: "<tool id='cat2'/>" });
        expect(mockEditor.setValue).toHaveBeenCalledWith("<tool id='cat2'/>");
    });

    it("updates the model language when the language changes", async () => {
        const wrapper = await mountToolSourceDisplay();
        await wrapper.setProps({ language: "yaml" });
        expect(mockMonaco.editor.setModelLanguage).toHaveBeenCalledWith(mockModel, "yaml");
    });

    it("disposes the editor on unmount", async () => {
        const wrapper = await mountToolSourceStory();
        expect(mockEditor.dispose).not.toHaveBeenCalled();
        wrapper.unmount();
        expect(mockEditor.dispose).toHaveBeenCalledTimes(1);
    });

    it("works with the Monaco editor itself rather than a reactive proxy of it", async () => {
        // Monaco calls back into its own internals through `this`; behind a Vue 3 proxy
        // that pins the tab once the tool source modal closes and disposes the editor.
        const wrapper = await mountToolSourceDisplay();
        await wrapper.setProps({ code: "<tool id='x' />" });
        wrapper.unmount();

        expect(mockEditor.setValue.mock.contexts[0]).toBe(mockEditor);
        expect(mockEditor.dispose).toHaveBeenCalledTimes(1);
        expect(mockEditor.dispose.mock.contexts[0]).toBe(mockEditor);
    });
});
