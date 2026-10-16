import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import MarkdownEditor from "./MarkdownEditor.vue";

const localVue = getLocalVue();

function mountEditor(props: Record<string, unknown> = {}) {
    return mount(MarkdownEditor as object, {
        props: { markdownText: "", mode: "page", title: "My Page", ...props },
        global: {
            ...localVue,
            stubs: { ...localVue.stubs, CellEditor: true, GModal: true, MarkdownHelp: true, TextEditor: true },
        },
    });
}

describe("MarkdownEditor", () => {
    it("offers the editor choice as named toggle buttons with Text selected", () => {
        const wrapper = mountEditor();
        const group = wrapper.find("[role=radiogroup]");
        expect(group.attributes("aria-label")).toBe("Editor");
        // inline like a button group, so the help button stays on the same row
        expect(group.classes()).toContain("d-inline-block");
        const buttons = group.findAll(".g-radio-button");
        expect(buttons.map((button) => button.text())).toEqual(["Editor", "Text"]);
        expect(buttons.every((button) => button.classes("g-outline") && button.classes("g-blue"))).toBe(true);
        expect(buttons.every((button) => button.classes("g-small"))).toBe(true);
        expect(group.find(".g-checked").text()).toBe("Text");
        expect(wrapper.find("text-editor-stub").exists()).toBe(true);
    });

    it("switches to the cell editor", async () => {
        const wrapper = mountEditor();
        await wrapper.findAll("input[type=radio]")[0]!.setValue(true);
        expect(wrapper.find("cell-editor-stub").exists()).toBe(true);
        expect(wrapper.find("text-editor-stub").exists()).toBe(false);
        expect(wrapper.find(".g-checked").text()).toBe("Editor");
    });

    it("hides the editor choice when labels are given", () => {
        const wrapper = mountEditor({ labels: [] });
        expect(wrapper.find("[role=radiogroup]").exists()).toBe(false);
    });
});
