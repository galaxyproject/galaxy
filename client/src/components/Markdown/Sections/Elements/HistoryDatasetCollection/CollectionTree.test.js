import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import { sanitizeHtml } from "@/directives/sanitizeHtml";

import CollectionTree from "./CollectionTree.vue";

describe("CollectionTree", () => {
    it("shows element info as text and renders peeks through v-sanitize-html", () => {
        vi.mocked(sanitizeHtml).mockClear();
        const peek = "<table><tr><td>row</td></tr></table>";
        const wrapper = mount(CollectionTree, {
            localVue: getLocalVue(),
            propsData: {
                node: {
                    name: "list",
                    elements: [{ id: "e1", element_identifier: "a", object: { misc_info: "<i>info</i>", peek } }],
                },
            },
        });

        const child = wrapper.findAllComponents(CollectionTree).at(1);
        const [info, peekBlock] = child.findAll("pre code").wrappers;
        expect(info.text()).toBe("<i>info</i>");
        expect(info.find("i").exists()).toBe(false);
        expect(sanitizeHtml).toHaveBeenCalledWith(peek, "default");
        expect(peekBlock.find("td").text()).toBe("row");
    });
});
