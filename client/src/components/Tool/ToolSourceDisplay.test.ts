import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";

import ToolSourceDisplay from "./ToolSourceDisplay.vue";

const editor = { dispose: vi.fn(), setValue: vi.fn(), getModel: vi.fn(), layout: vi.fn() };

vi.mock("@monaco-editor/loader", () => ({
    default: { init: () => Promise.resolve({ editor: { create: () => editor } }) },
}));

describe("ToolSourceDisplay", () => {
    it("works with the Monaco editor itself rather than a reactive proxy of it", async () => {
        // Monaco calls back into its own internals through `this`; behind a Vue 3 proxy
        // that pins the tab once the tool source modal closes and disposes the editor.
        const wrapper = mount(ToolSourceDisplay, { props: { language: "xml", code: "<tool />" } });
        await flushPromises();

        await wrapper.setProps({ code: "<tool id='x' />" });
        wrapper.unmount();

        expect(editor.setValue.mock.contexts[0]).toBe(editor);
        expect(editor.dispose).toHaveBeenCalledTimes(1);
        expect(editor.dispose.mock.contexts[0]).toBe(editor);
    });
});
