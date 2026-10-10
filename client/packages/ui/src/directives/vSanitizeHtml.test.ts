import { mount, type VueWrapper } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { defineComponent } from "vue";

import { sanitizeHtml } from "./sanitizeHtml";

// The directive is registered globally by the test setup, with sanitizeHtml
// replaced by a pass-through spy; here it is swapped for a marker so the tests
// can tell sanitized output apart from the raw input.
const sanitizeSpy = vi.mocked(sanitizeHtml);

function mountWith(value: unknown, profile?: string) {
    const directive = profile ? `v-sanitize-html:${profile}` : "v-sanitize-html";
    const Host = defineComponent({
        props: {
            value: { type: null, default: null },
            other: { type: Number, default: 0 },
            rich: { type: Boolean, default: true },
        },
        template: `<div><span data-other>{{ other }}</span><div v-if="rich" class="target" ${directive}="value" /><div v-else class="target">plain</div></div>`,
    });
    return mount(Host, { props: { value } });
}

function targetOf(wrapper: VueWrapper) {
    return wrapper.find(".target").element;
}

describe("v-sanitize-html", () => {
    beforeEach(() => {
        sanitizeSpy.mockReset();
        sanitizeSpy.mockImplementation((html) => `<i>sanitized:${html}</i>`);
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    test("renders the sanitizer output for a string with the default profile", () => {
        const wrapper = mountWith("<b>hello</b>");

        expect(sanitizeSpy).toHaveBeenCalledWith("<b>hello</b>", "default");
        expect(targetOf(wrapper).innerHTML).toBe("<i>sanitized:<b>hello</b></i>");
    });

    test("uses the directive argument as the profile", () => {
        const wrapper = mountWith("<a>x</a>", "links");

        expect(sanitizeSpy).toHaveBeenCalledWith("<a>x</a>", "links");
        expect(targetOf(wrapper).innerHTML).toBe("<i>sanitized:<a>x</a></i>");
    });

    test.each([null, undefined])("treats %s as empty", (value) => {
        const wrapper = mountWith(value);

        expect(sanitizeSpy.mock.calls).toEqual([["", "default"]]);
        expect(targetOf(wrapper).innerHTML).toBe("<i>sanitized:</i>");
    });

    test.each([
        ["an object", { nested: "message" }],
        ["an array", ["a", "b"]],
        ["a number", 42],
    ])("renders nothing and warns for %s", (_kind, value) => {
        const warn = vi.spyOn(console, "warn").mockImplementation(() => {});

        const wrapper = mountWith(value);

        expect(sanitizeSpy.mock.calls).toEqual([["", "default"]]);
        expect(targetOf(wrapper).innerHTML).toBe("<i>sanitized:</i>");
        expect(warn).toHaveBeenCalledOnce();
        expect(warn).toHaveBeenCalledWith("v-sanitize-html expects a string, got:", value);
    });

    test("re-sanitizes when the bound value changes", async () => {
        const wrapper = mountWith("first", "links");

        await wrapper.setProps({ value: "second" });

        expect(sanitizeSpy).toHaveBeenLastCalledWith("second", "links");
        expect(targetOf(wrapper).innerHTML).toBe("<i>sanitized:second</i>");
    });

    test("leaves the DOM alone when an unrelated re-render keeps the same content", async () => {
        const wrapper = mountWith("same", "links");
        const target = targetOf(wrapper);
        target.querySelector("i")!.setAttribute("data-decorated", "yes");
        sanitizeSpy.mockClear();

        await wrapper.setProps({ other: 1 });

        expect(wrapper.find("[data-other]").text()).toBe("1");
        expect(sanitizeSpy).not.toHaveBeenCalled();
        expect(target.querySelector("i")!.getAttribute("data-decorated")).toBe("yes");
    });

    test("clears its markup when a reused element no longer has the directive", async () => {
        const wrapper = mountWith("<b>rich</b>");
        expect(targetOf(wrapper).innerHTML).toBe("<i>sanitized:<b>rich</b></i>");

        await wrapper.setProps({ rich: false });

        expect(targetOf(wrapper).innerHTML).toBe("plain");
    });

    test("keeps its markup while the element is being destroyed", () => {
        const wrapper = mountWith("content");
        const target = targetOf(wrapper);

        wrapper.unmount();

        expect(target.innerHTML).toBe("<i>sanitized:content</i>");
    });
});
