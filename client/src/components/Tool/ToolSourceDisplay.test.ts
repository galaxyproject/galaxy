import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ToolSourceDisplay from "./ToolSourceDisplay.vue";

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
    default: { init: vi.fn(() => Promise.resolve(mockMonaco)) },
}));

async function mountToolSourceDisplay() {
    const wrapper = mount(ToolSourceDisplay as object, {
        propsData: { code: "<tool id='cat1'/>", language: "xml" },
    });
    await flushPromises();
    return wrapper;
}

describe("ToolSourceDisplay", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("creates a read-only editor in its container", async () => {
        const wrapper = await mountToolSourceDisplay();
        expect(mockMonaco.editor.create).toHaveBeenCalledTimes(1);
        expect(mockMonaco.editor.create).toHaveBeenCalledWith(
            wrapper.find(".editor-container").element,
            expect.objectContaining({ value: "<tool id='cat1'/>", language: "xml", readOnly: true }),
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
        const wrapper = await mountToolSourceDisplay();
        expect(mockEditor.dispose).not.toHaveBeenCalled();
        wrapper.destroy();
        expect(mockEditor.dispose).toHaveBeenCalledTimes(1);
    });
});
