import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import CodeRow from "./CodeRow.vue";

const localVue = getLocalVue();

function mountCodeRow(codeItem: string) {
    return mount(CodeRow as object, {
        props: { codeLabel: "Tool Standard Output", codeItem },
        global: { ...localVue, stubs: { HelpText: true } },
    });
}

describe("CodeRow", () => {
    it("offers expanding short multi-line content, which the one-line preview folds together", async () => {
        const wrapper = mountCodeRow("first line\nsecond line\n");
        await wrapper.vm.$nextTick();

        const toggle = wrapper.find(".code-row-toggle");
        expect(toggle.exists()).toBe(true);
        await toggle.trigger("click");
        expect(wrapper.find("pre").classes()).not.toContain("preview");
    });

    it("does not offer expanding a single line that fits", async () => {
        const wrapper = mountCodeRow("one line\n");
        await wrapper.vm.$nextTick();

        expect(wrapper.find(".code-row-toggle").exists()).toBe(false);
    });
});
