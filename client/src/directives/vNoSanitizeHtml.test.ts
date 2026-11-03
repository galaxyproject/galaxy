import { mount, type VueWrapper } from "@vue/test-utils";
import { beforeEach, describe, expect, test, vi } from "vitest";
import { defineComponent, type PropType } from "vue";

import { sanitizeHtml } from "@/directives/sanitizeHtml";

// The directive is registered globally by the test setup, where sanitizeHtml is
// a spy; these tests check that v-no-sanitize-html never reaches it.
const sanitizeSpy = vi.mocked(sanitizeHtml);

function mountWith(value: string | null) {
    const Host = defineComponent({
        props: {
            value: { type: String as PropType<string | null>, default: null },
            other: { type: Number, default: 0 },
            rich: { type: Boolean, default: true },
        },
        template: `<div><span data-other>{{ other }}</span><div v-if="rich" class="target" v-no-sanitize-html="value" /><div v-else class="target">plain</div></div>`,
    });
    return mount(Host, { props: { value } });
}

function targetOf(wrapper: VueWrapper) {
    return wrapper.find(".target").element;
}

describe("v-no-sanitize-html", () => {
    beforeEach(() => {
        sanitizeSpy.mockClear();
    });

    test("sets the markup as given, without the sanitizer", () => {
        const wrapper = mountWith("<em>from server config</em>");

        expect(targetOf(wrapper).innerHTML).toBe("<em>from server config</em>");
        expect(sanitizeSpy).not.toHaveBeenCalled();
    });

    test("replaces the markup when the bound value changes", async () => {
        const wrapper = mountWith("<em>from server config</em>");

        await wrapper.setProps({ value: "<strong>changed</strong>" });

        expect(targetOf(wrapper).innerHTML).toBe("<strong>changed</strong>");
        expect(sanitizeSpy).not.toHaveBeenCalled();
    });

    test("renders nothing when mounted with null", () => {
        const wrapper = mountWith(null);

        expect(targetOf(wrapper).innerHTML).toBe("");
    });

    test("clears the markup when the bound value becomes null", async () => {
        const wrapper = mountWith("<strong>changed</strong>");

        await wrapper.setProps({ value: null });

        expect(targetOf(wrapper).innerHTML).toBe("");
    });

    test("leaves the DOM alone when an unrelated re-render keeps the same content", async () => {
        const wrapper = mountWith("<i>same</i>");
        const target = targetOf(wrapper);
        target.querySelector("i")!.setAttribute("data-decorated", "yes");

        await wrapper.setProps({ other: 1 });

        expect(wrapper.find("[data-other]").text()).toBe("1");
        expect(target.querySelector("i")!.getAttribute("data-decorated")).toBe("yes");
    });

    test("clears its markup when a reused element no longer has the directive", async () => {
        const wrapper = mountWith("<b>rich</b>");
        expect(targetOf(wrapper).innerHTML).toBe("<b>rich</b>");

        await wrapper.setProps({ rich: false });

        expect(targetOf(wrapper).innerHTML).toBe("plain");
    });

    test("keeps its markup while the element is being destroyed", () => {
        const wrapper = mountWith("content");
        const target = targetOf(wrapper);

        wrapper.unmount();

        expect(target.innerHTML).toBe("content");
    });
});
