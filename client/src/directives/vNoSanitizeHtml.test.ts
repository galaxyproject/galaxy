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

    test("clears its markup when a reused element no longer has the directive", async () => {
        const Host = defineComponent({
            props: { rich: { type: Boolean, default: true } },
            template: `<div><pre v-if="rich" v-no-sanitize-html="'<b>rich</b>'" /><pre v-else class="plain">plain</pre></div>`,
        });
        const wrapper = mount(Host as object, { propsData: { rich: true } });
        expect(wrapper.find("pre").element.innerHTML).toBe("<b>rich</b>");

        await wrapper.setProps({ rich: false });
        expect(wrapper.find("pre").element.innerHTML).toBe("plain");
    });
});
