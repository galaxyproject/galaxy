import { mount } from "@vue/test-utils";
import { describe, expect, test } from "vitest";
import { defineComponent } from "vue";

import { sanitizeHtml } from "@/directives/sanitizeHtml";

function mountWith(value: string | null) {
    const Host = defineComponent({
        props: { value: { type: String, default: null } },
        template: `<div v-no-sanitize-html="value" />`,
    });
    return mount(Host as object, { propsData: { value } });
}

describe("v-no-sanitize-html", () => {
    test("sets the markup as given, without the sanitizer", async () => {
        const wrapper = mountWith("<em>from server config</em>");
        expect(wrapper.element.innerHTML).toBe("<em>from server config</em>");
        expect(sanitizeHtml).not.toHaveBeenCalled();

        await wrapper.setProps({ value: "<strong>changed</strong>" });
        expect(wrapper.element.innerHTML).toBe("<strong>changed</strong>");

        await wrapper.setProps({ value: null });
        expect(wrapper.element.innerHTML).toBe("");
    });
});
